"""Segment DSL — the typed, validated language the AI (and the UI) use to define audiences.

The LLM **never writes SQL**. It emits a Segment DSL document (a small JSON tree); this module
validates it against a *closed allowlist* of fields and operators. `compiler.py` then turns a
validated document into **parameterized** SQL.

Because fields and operators are allowlisted, and every value is bound as a parameter (never
string-concatenated), the DSL is injection-safe *by construction* — which is exactly what makes
LLM-proposed segments safe to execute against a production database.

Example document::

    {
      "version": 1,
      "match": "all",
      "rules": [
        {"field": "days_since_last_order", "op": "gte", "value": 60},
        {"match": "any", "rules": [
          {"field": "city", "op": "eq", "value": "Mumbai"},
          {"field": "city", "op": "eq", "value": "Delhi"}
        ]}
      ]
    }
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

FieldType = Literal["numeric", "bool", "text"]

# Guard rails against pathological documents from a model.
MAX_DEPTH = 5
MAX_CONDITIONS = 50


@dataclass(frozen=True)
class FieldDef:
    """A filterable field mapped to a SQL expression over the `customers` table."""

    type: FieldType
    sql: str


# Closed allowlist of filterable fields. A field the model asks for that is not here is rejected.
FIELDS: dict[str, FieldDef] = {
    "total_spend": FieldDef("numeric", "customers.total_spend"),
    "total_orders": FieldDef("numeric", "customers.total_orders"),
    "ltv": FieldDef("numeric", "customers.ltv"),
    "avg_order_value": FieldDef(
        "numeric", "(customers.total_spend / NULLIF(customers.total_orders, 0))"
    ),
    "days_since_last_order": FieldDef(
        "numeric", "(EXTRACT(EPOCH FROM (now() - customers.last_order_at)) / 86400.0)"
    ),
    "days_since_signup": FieldDef(
        "numeric", "(EXTRACT(EPOCH FROM (now() - customers.created_at)) / 86400.0)"
    ),
    "whatsapp_opt_in": FieldDef("bool", "customers.whatsapp_opt_in"),
    "email_opt_in": FieldDef("bool", "customers.email_opt_in"),
    "city": FieldDef("text", "customers.city"),
}

OPS_BY_TYPE: dict[FieldType, set[str]] = {
    "numeric": {"eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in"},
    "bool": {"is_true", "is_false", "eq"},
    "text": {"eq", "ne", "in", "not_in"},
}

LIST_OPS = {"in", "not_in"}
NULLARY_OPS = {"is_true", "is_false"}


def _check_scalar_types(ftype: FieldType, values: list[Any]) -> None:
    for v in values:
        if ftype == "numeric":
            # bool is a subclass of int — reject it explicitly.
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(f"numeric field requires a number, got {v!r}")
        elif ftype == "text":
            if not isinstance(v, str):
                raise ValueError(f"text field requires a string, got {v!r}")
        elif ftype == "bool":
            if not isinstance(v, bool):
                raise ValueError(f"bool field requires true/false, got {v!r}")


class Condition(BaseModel):
    """A single `field op value` predicate."""

    model_config = ConfigDict(extra="forbid")

    field: str
    op: str
    value: Any = None

    @model_validator(mode="after")
    def _validate(self) -> "Condition":
        if self.field not in FIELDS:
            raise ValueError(
                f"unknown field {self.field!r}; allowed: {sorted(FIELDS)}"
            )
        ftype = FIELDS[self.field].type
        if self.op not in OPS_BY_TYPE[ftype]:
            raise ValueError(
                f"operator {self.op!r} is not valid for {ftype} field {self.field!r}; "
                f"allowed: {sorted(OPS_BY_TYPE[ftype])}"
            )

        if self.op in NULLARY_OPS:
            if self.value not in (None, True, False):
                raise ValueError(f"operator {self.op!r} takes no value")
        elif self.op in LIST_OPS:
            if not isinstance(self.value, list) or not self.value:
                raise ValueError(f"operator {self.op!r} requires a non-empty list value")
            _check_scalar_types(ftype, self.value)
        else:
            if isinstance(self.value, (list, dict)):
                raise ValueError(f"operator {self.op!r} requires a scalar value")
            _check_scalar_types(ftype, [self.value])
        return self


class Group(BaseModel):
    """A boolean group: combine child rules with AND (`all`) or OR (`any`)."""

    model_config = ConfigDict(extra="forbid")

    match: Literal["all", "any"] = "all"
    rules: list[Union["Condition", "Group"]] = Field(default_factory=list)


class SegmentDSL(BaseModel):
    """A complete segment definition (a versioned root group)."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    match: Literal["all", "any"] = "all"
    rules: list[Union["Condition", "Group"]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _guard_complexity(self) -> "SegmentDSL":
        total = _walk(self.rules, depth=1)
        if total > MAX_CONDITIONS:
            raise ValueError(f"too many conditions ({total} > {MAX_CONDITIONS})")
        return self


def _walk(rules: list[Union[Condition, Group]], depth: int) -> int:
    if depth > MAX_DEPTH:
        raise ValueError(f"segment nesting too deep (> {MAX_DEPTH})")
    count = 0
    for r in rules:
        if isinstance(r, Group):
            count += _walk(r.rules, depth + 1)
        else:
            count += 1
    return count


# Resolve the forward references in the recursive unions.
Group.model_rebuild()
SegmentDSL.model_rebuild()

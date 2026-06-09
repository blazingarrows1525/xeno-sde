"""Deterministic compiler: a validated Segment DSL document -> parameterized SQL.

The output is a `WHERE` clause plus a dict of bound parameters. Values are **never** inlined
into the SQL string — they are always returned as named bind parameters (`:p0`, `:p1`, ...),
which the database driver binds safely. This is the property that makes executing an
LLM-proposed segment safe.

The compiled clause is designed to run against the `customers` table::

    SELECT count(*) FROM customers WHERE <where_sql>          -- estimated size
    SELECT customers.id FROM customers WHERE <where_sql> ...  -- materialize membership
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Union

from app.segments.dsl import FIELDS, Condition, Group, SegmentDSL

# op -> SQL template. `{expr}` is the field's SQL expression, `{p}` the bound param name.
_PREDICATES: dict[str, str] = {
    "eq": "{expr} = :{p}",
    "ne": "{expr} <> :{p}",
    "gt": "{expr} > :{p}",
    "gte": "{expr} >= :{p}",
    "lt": "{expr} < :{p}",
    "lte": "{expr} <= :{p}",
    "in": "{expr} = ANY(:{p})",
    "not_in": "NOT ({expr} = ANY(:{p}))",
}


@dataclass
class _ParamGen:
    """Generates unique, ordered bind-parameter names and collects their values."""

    i: int = 0
    params: dict[str, Any] = field(default_factory=dict)

    def add(self, value: Any) -> str:
        name = f"p{self.i}"
        self.i += 1
        self.params[name] = value
        return name


@dataclass
class Compiled:
    """A compiled segment: a parameterized WHERE clause and its bound parameters."""

    where_sql: str
    params: dict[str, Any]

    def count_sql(self) -> str:
        return f"SELECT count(*) AS n FROM customers WHERE {self.where_sql}"

    def select_ids_sql(self, limit: int | None = None) -> str:
        sql = (
            f"SELECT customers.id FROM customers WHERE {self.where_sql} "
            "ORDER BY customers.ltv DESC NULLS LAST"
        )
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        return sql


def compile_segment(dsl: SegmentDSL) -> Compiled:
    gen = _ParamGen()
    where = _compile_group(dsl.match, dsl.rules, gen)
    return Compiled(where_sql=where, params=gen.params)


def _compile_node(node: Union[Condition, Group], gen: _ParamGen) -> str:
    if isinstance(node, Group):
        return _compile_group(node.match, node.rules, gen)
    return _compile_condition(node, gen)


def _compile_group(
    match: str, rules: list[Union[Condition, Group]], gen: _ParamGen
) -> str:
    if not rules:
        return "TRUE"  # an empty group matches everyone
    joiner = " AND " if match == "all" else " OR "
    return "(" + joiner.join(_compile_node(r, gen) for r in rules) + ")"


def _compile_condition(c: Condition, gen: _ParamGen) -> str:
    expr = FIELDS[c.field].sql
    if c.op == "is_true":
        return f"{expr} IS TRUE"
    if c.op == "is_false":
        return f"{expr} IS FALSE"
    pname = gen.add(c.value)
    return _PREDICATES[c.op].format(expr=expr, p=pname)

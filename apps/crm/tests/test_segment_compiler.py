"""Tests for the Segment DSL + compiler.

These double as the safety argument for executing LLM-proposed segments: unknown fields are
rejected, operators are type-checked, and every value is a *bound parameter* — never inlined
into SQL.
"""
import pytest
from pydantic import ValidationError

from app.segments import SegmentDSL, compile_segment


# ----- compilation -----------------------------------------------------------------------


def test_numeric_condition_binds_value_not_inlines_it():
    dsl = SegmentDSL(rules=[{"field": "days_since_last_order", "op": "gte", "value": 60}])
    c = compile_segment(dsl)
    assert ":p0" in c.where_sql
    assert "EXTRACT(EPOCH" in c.where_sql  # computed expression, not a raw column
    assert c.params == {"p0": 60}
    assert "60" not in c.where_sql  # the literal is bound, never concatenated


def test_nested_all_any_groups_produce_and_or_with_parens():
    dsl = SegmentDSL(
        match="all",
        rules=[
            {"field": "total_orders", "op": "gte", "value": 1},
            {
                "match": "any",
                "rules": [
                    {"field": "city", "op": "eq", "value": "Mumbai"},
                    {"field": "city", "op": "eq", "value": "Delhi"},
                ],
            },
        ],
    )
    c = compile_segment(dsl)
    assert " AND " in c.where_sql
    assert " OR " in c.where_sql
    assert c.where_sql.count("(") >= 2
    assert c.params == {"p0": 1, "p1": "Mumbai", "p2": "Delhi"}


def test_in_operator_uses_any_with_list_param():
    dsl = SegmentDSL(rules=[{"field": "city", "op": "in", "value": ["Mumbai", "Pune"]}])
    c = compile_segment(dsl)
    assert "= ANY(:p0)" in c.where_sql
    assert c.params["p0"] == ["Mumbai", "Pune"]


def test_not_in_negates_any():
    dsl = SegmentDSL(rules=[{"field": "city", "op": "not_in", "value": ["Goa"]}])
    c = compile_segment(dsl)
    assert c.where_sql.startswith("(NOT (")
    assert c.params["p0"] == ["Goa"]


def test_bool_is_true_has_no_params():
    dsl = SegmentDSL(rules=[{"field": "whatsapp_opt_in", "op": "is_true"}])
    c = compile_segment(dsl)
    assert "customers.whatsapp_opt_in IS TRUE" in c.where_sql
    assert c.params == {}


def test_empty_rules_match_everyone():
    c = compile_segment(SegmentDSL())
    assert c.where_sql == "TRUE"


def test_count_and_ids_sql_shape():
    c = compile_segment(SegmentDSL(rules=[{"field": "ltv", "op": "gte", "value": 1000}]))
    assert c.count_sql().startswith("SELECT count(*)")
    assert "FROM customers WHERE" in c.count_sql()
    assert "LIMIT 5" in c.select_ids_sql(limit=5)


# ----- validation / safety ---------------------------------------------------------------


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        SegmentDSL(rules=[{"field": "password_hash", "op": "eq", "value": "x"}])


def test_operator_must_match_field_type():
    with pytest.raises(ValidationError):
        SegmentDSL(rules=[{"field": "city", "op": "gt", "value": "Mumbai"}])


def test_numeric_field_rejects_non_number():
    with pytest.raises(ValidationError):
        SegmentDSL(rules=[{"field": "total_spend", "op": "eq", "value": "a-lot"}])


def test_numeric_field_rejects_bool():
    with pytest.raises(ValidationError):
        SegmentDSL(rules=[{"field": "total_spend", "op": "eq", "value": True}])


def test_in_requires_non_empty_list():
    with pytest.raises(ValidationError):
        SegmentDSL(rules=[{"field": "city", "op": "in", "value": []}])


def test_extra_keys_are_forbidden():
    with pytest.raises(ValidationError):
        SegmentDSL(rules=[{"field": "ltv", "op": "gte", "value": 1, "sneaky": "drop"}])


def test_sql_injection_value_is_bound_never_concatenated():
    evil = "Mumbai'); DROP TABLE customers;--"
    dsl = SegmentDSL(rules=[{"field": "city", "op": "eq", "value": evil}])
    c = compile_segment(dsl)
    assert evil not in c.where_sql          # the payload never reaches the SQL string
    assert c.params["p0"] == evil           # it is always a bound parameter
    assert "DROP TABLE" not in c.where_sql


def test_nesting_depth_is_capped():
    node: dict = {"field": "ltv", "op": "gte", "value": 1}
    for _ in range(6):  # exceed MAX_DEPTH
        node = {"match": "all", "rules": [node]}
    with pytest.raises(ValidationError):
        SegmentDSL(rules=[node])

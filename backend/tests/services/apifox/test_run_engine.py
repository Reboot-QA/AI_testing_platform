"""S2 条件求值单元 · run_engine.evaluate_condition（操作符/插值/缺失变量/边界）。"""

import pytest

from app.services.apifox.run_engine import evaluate_condition


@pytest.mark.parametrize(
    "operator,left,right,expected",
    [
        ("eq", "a", "a", True),
        ("eq", "a", "b", False),
        ("neq", "a", "b", True),
        ("neq", "a", "a", False),
        ("contains", "hello world", "world", True),
        ("contains", "hello", "x", False),
        ("not_contains", "hello", "x", True),
        ("gt", "5", "3", True),
        ("gt", "3", "5", False),
        ("gte", "3", "3", True),
        ("lt", "2", "3", True),
        ("lte", "3", "3", True),
        ("regex", "abc123", r"\d+", True),
        ("regex", "abc", r"\d+", False),
    ],
)
def test_operators(operator, left, right, expected):
    ok, _ = evaluate_condition({"left": left, "operator": operator, "right": right}, {})

    assert ok is expected


def test_interpolates_left_from_variables():
    ok, _ = evaluate_condition(
        {"left": "{{token}}", "operator": "eq", "right": "abc"}, {"token": "abc"}
    )

    assert ok is True


def test_interpolates_right_from_variables():
    ok, _ = evaluate_condition(
        {"left": "abc", "operator": "eq", "right": "{{expected}}"}, {"expected": "abc"}
    )

    assert ok is True


def test_exists_true_when_var_defined_nonempty():
    ok, _ = evaluate_condition({"left": "{{token}}", "operator": "exists"}, {"token": "v"})

    assert ok is True


def test_exists_false_when_var_missing():
    ok, _ = evaluate_condition({"left": "{{token}}", "operator": "exists"}, {})

    assert ok is False


def test_missing_var_comparison_is_determinate_not_crash():
    ok, _ = evaluate_condition({"left": "{{missing}}", "operator": "eq", "right": "x"}, {})

    assert ok is False


def test_gt_nonnumeric_is_false_not_crash():
    ok, _ = evaluate_condition({"left": "abc", "operator": "gt", "right": "3"}, {})

    assert ok is False

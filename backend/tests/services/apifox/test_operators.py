"""operators._apply_operator 单元 · 各操作符的等价类与边界（含非数值/无效正则/None）。"""

import pytest

from app.services.apifox.operators import _apply_operator


@pytest.mark.parametrize(
    "actual,expected,operator,passed",
    [
        ("a", "a", "eq", True),
        ("a", "b", "eq", False),
        ("a", "b", "neq", True),
        ("a", "a", "neq", False),
        ("hello world", "world", "contains", True),
        ("hello", "x", "contains", False),
        ("hello", "x", "not_contains", True),
        ("hello", "ell", "not_contains", False),
    ],
)
def test_string_operator_compares_as_expected(actual, expected, operator, passed):
    ok, _ = _apply_operator(actual, expected, operator)

    assert ok is passed


@pytest.mark.parametrize(
    "actual,expected,operator,passed",
    [
        (5, "3", "gt", True),
        (3, "5", "gt", False),
        (3, "3", "gt", False),
        (3, "3", "gte", True),
        (2, "3", "lt", True),
        (3, "3", "lt", False),
        (3, "3", "lte", True),
        (4, "3", "lte", False),
    ],
)
def test_numeric_operator_compares_at_boundary(actual, expected, operator, passed):
    ok, _ = _apply_operator(actual, expected, operator)

    assert ok is passed


@pytest.mark.parametrize("operator", ["gt", "gte", "lt", "lte"])
def test_numeric_operator_nonnumeric_is_false_not_crash(operator):
    ok, _ = _apply_operator("abc", "3", operator)

    assert ok is False


@pytest.mark.parametrize(
    "actual,pattern,passed",
    [("abc123", r"\d+", True), ("abc", r"\d+", False)],
)
def test_regex_operator_matches(actual, pattern, passed):
    ok, _ = _apply_operator(actual, pattern, "regex")

    assert ok is passed


def test_regex_operator_invalid_pattern_is_false_not_crash():
    ok, _ = _apply_operator("abc", "(", "regex")

    assert ok is False


@pytest.mark.parametrize(
    "actual,passed",
    [("value", True), ("", True), (0, True), (None, False)],
)
def test_exists_operator_true_only_when_actual_not_none(actual, passed):
    ok, _ = _apply_operator(actual, None, "exists")

    assert ok is passed


def test_none_actual_equals_empty_string_under_eq():
    ok, _ = _apply_operator(None, "", "eq")

    assert ok is True


def test_empty_operator_defaults_to_eq():
    ok, _ = _apply_operator("a", "a", "")

    assert ok is True

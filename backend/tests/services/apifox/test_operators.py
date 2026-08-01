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
        # 状态码 != 200 的真实场景：实际 200(int) vs 期望 "200"(str)，应判失败
        (200, "200", "neq", False),
        (201, "200", "neq", True),
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


@pytest.mark.parametrize("operator", ["ne", "!=", "not_equal", "乱写"])
def test_unknown_operator_never_silently_passes(operator):
    # 无法识别的运算符绝不能静默按 eq 判「通过」，否则 != 等被降级成 == 造成假通过
    ok, msg = _apply_operator(200, "200", operator)

    assert ok is False
    assert "未知操作符" in msg


@pytest.mark.parametrize(
    "actual,expected,operator,passed",
    [
        (True, "true", "eq", True),  # JSON bool True vs 期望 "true" → 应通过（此前 "True"!="true" 恒失败）
        (False, "false", "eq", True),
        (True, "false", "eq", False),
        (True, "true", "neq", False),
        (False, "true", "neq", True),
        (True, "True", "eq", True),  # 容忍 expected 大小写
        (True, " true ", "eq", True),  # 容忍空白
    ],
)
def test_bool_actual_compares_as_json_lowercase(actual, expected, operator, passed):
    ok, _ = _apply_operator(actual, expected, operator)

    assert ok is passed


def test_empty_operator_defaults_to_eq():
    # None/空串按历史默认 eq（存量默认「状态码==200」断言不设 operator，须保持）
    assert _apply_operator(200, "200", "")[0] is True
    assert _apply_operator(200, "200", None)[0] is True
    assert _apply_operator("a", "a", "")[0] is True


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

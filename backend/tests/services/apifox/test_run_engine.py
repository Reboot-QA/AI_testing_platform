"""S2/S3 执行引擎纯函数单元 · evaluate_condition（条件）+ loop_iterations（循环迭代序列）。"""

import pytest

from app.services.apifox.run_engine import MAX_LOOP_ITERATIONS, evaluate_condition, loop_iterations


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


# ---------- S3 循环迭代序列（count / list）----------
def test_count_mode_injects_zero_based_index():
    its = loop_iterations({"mode": "count", "count": 3}, {})

    assert its == [{"index": "0"}, {"index": "1"}, {"index": "2"}]


def test_count_mode_custom_index_var():
    its = loop_iterations({"mode": "count", "count": 2, "index_var": "i"}, {})

    assert [x["i"] for x in its] == ["0", "1"]


def test_list_mode_injects_item_and_index():
    its = loop_iterations(
        {"mode": "list", "list_var": "items", "item_var": "it"}, {"items": '["a", "b"]'}
    )

    assert its == [{"it": "a", "index": "0"}, {"it": "b", "index": "1"}]


def test_list_mode_object_element_serialized_to_json():
    its = loop_iterations(
        {"mode": "list", "list_var": "rows", "item_var": "row"}, {"rows": '[{"id": 1}]'}
    )

    assert its[0]["row"] == '{"id": 1}'


@pytest.mark.parametrize("raw", ["", "not-json", '{"a": 1}', "[]"])
def test_list_mode_missing_or_invalid_yields_no_iterations(raw):
    its = loop_iterations({"mode": "list", "list_var": "v", "item_var": "it"}, {"v": raw})

    assert its == []


def test_count_mode_capped_at_hard_limit():
    its = loop_iterations({"mode": "count", "count": MAX_LOOP_ITERATIONS + 500}, {})

    assert len(its) == MAX_LOOP_ITERATIONS


def test_while_mode_not_precomputed():
    assert loop_iterations({"mode": "while"}, {}) == []

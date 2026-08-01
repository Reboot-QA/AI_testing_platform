"""JSONPath 数组通配符 `[*]`：断言取值(_extract_json_path)与提取取值(resolve_json_path)两套解析。"""

from app.services.apifox.assertions import _extract_json_path
from app.services.apifox.json_path import resolve_json_path

DATA = {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}


def test_assertion_extract_supports_wildcard_field():
    assert _extract_json_path(DATA, "$.items[*].id") == [1, 2, 3]


def test_assertion_extract_wildcard_last_segment_returns_elements():
    assert _extract_json_path(DATA, "$.items[*]") == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_assertion_extract_wildcard_on_non_list_is_none():
    assert _extract_json_path({"items": {"id": 1}}, "$.items[*].id") is None


def test_assertion_extract_plain_path_unchanged():
    assert _extract_json_path(DATA, "$.items[1].id") == 2  # 无通配符路径行为不变


def test_resolve_supports_wildcard_field():
    found, value = resolve_json_path(DATA, "$.items[*].id")
    assert found is True
    assert value == [1, 2, 3]


def test_resolve_wildcard_missing_field_yields_none_per_item():
    found, value = resolve_json_path({"items": [{"id": 1}, {"x": 2}]}, "$.items[*].id")
    assert found is True
    assert value == [1, None]

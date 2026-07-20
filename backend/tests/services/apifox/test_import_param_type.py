"""导入接口 · Params 类型回填 + 必选参数默认勾选（enabled=required）。"""

import pytest

from app.services.apifox.import_service import _form_rows, _param_type, _rows_from_params


@pytest.mark.parametrize(
    "param,expected",
    [
        ({"schema": {"type": "integer"}}, "integer"),  # OpenAPI3
        ({"type": "boolean"}, "boolean"),  # Swagger2
        ({}, "string"),  # 无类型信息 → 默认
        ({"schema": {"type": "file"}}, "string"),  # 不在允许集合 → 回退
        ({"schema": {"type": "integer"}, "type": "string"}, "integer"),  # schema 优先
    ],
)
def test_param_type_maps_source_type_or_falls_back(param, expected):
    assert _param_type(param) == expected


def test_rows_from_params_backfills_type():
    params = [
        {"in": "query", "name": "page", "schema": {"type": "integer"}},
        {"in": "query", "name": "q", "schema": {"type": "string"}},
        {"in": "path", "name": "id", "schema": {"type": "integer"}},
    ]

    rows = _rows_from_params({}, params, "query")

    assert [(r.key, r.type) for r in rows] == [("page", "integer"), ("q", "string")]


def test_rows_from_params_enabled_only_when_required():
    params = [
        {"in": "query", "name": "page", "required": True, "schema": {"type": "integer"}},
        {"in": "query", "name": "q", "schema": {"type": "string"}},  # 无 required
        {"in": "query", "name": "size", "required": False, "schema": {"type": "integer"}},
    ]

    rows = _rows_from_params({}, params, "query")

    assert [(r.key, r.enabled) for r in rows] == [("page", True), ("q", False), ("size", False)]


def test_form_rows_enabled_only_when_required():
    schema = {
        "type": "object",
        "required": ["username"],
        "properties": {"username": {"type": "string"}, "nickname": {"type": "string"}},
    }

    enabled = {r.key: r.enabled for r in _form_rows({}, schema)}

    assert enabled["username"] is True
    assert enabled["nickname"] is False

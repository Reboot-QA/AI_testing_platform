"""导入接口 · Params 类型回填 · OpenAPI3(schema.type) / Swagger2(param.type) / 默认回退。"""

import pytest

from app.services.apifox.import_service import _param_type, _rows_from_params


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

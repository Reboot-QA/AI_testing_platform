"""契约校验：忽略 OpenAPI 专有 format（password/binary 等），只校验结构/类型。

背景：FastAPI/OpenAPI 会给密码字段生成 `format: password`（标准写法，仅 UI 提示）；
fastjsonschema 默认对不认识的 format 直接编译失败（不符合 JSON Schema"未知 format 应忽略"），
导致导入的模型做契约校验报"契约 schema 无效：Unknown format: password"。
"""

import json

import httpx

from app.services.apifox import contract_service


def _resp(body: dict) -> httpx.Response:
    return httpx.Response(200, json=body, request=httpx.Request("POST", "http://x/"))


def test_contract_ignores_openapi_only_format_password():
    schema = json.dumps(
        {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "password": {"type": "string", "format": "password"},
            },
            "required": ["username", "password"],
        }
    )

    result = contract_service.validate_response(schema, _resp({"username": "a", "password": "x"}))

    assert result["passed"] is True  # 修复前：format:password 让编译失败 → "契约 schema 无效"


def test_contract_still_validates_structure_after_ignoring_format():
    """忽略 format 不削弱结构/类型校验：缺必填仍判不符。"""
    schema = json.dumps(
        {
            "type": "object",
            "properties": {"password": {"type": "string", "format": "password"}},
            "required": ["password"],
        }
    )

    result = contract_service.validate_response(schema, _resp({}))  # 缺 password

    assert result["passed"] is False

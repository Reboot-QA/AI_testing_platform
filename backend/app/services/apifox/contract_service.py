"""Apifox 契约校验：按数据模型（JSON Schema）校验响应体。用 fastjsonschema（纯 Python，离线友好）。"""

import json
from typing import Any, Dict, List

import fastjsonschema
import httpx


def _fail(message: str, errors: List[str] | None = None) -> Dict[str, Any]:
    return {"passed": False, "message": message, "errors": errors or [message]}


def validate_response(json_schema_text: str, response: httpx.Response) -> Dict[str, Any]:
    """返回 {passed, message, errors}。全程不抛异常（校验类工具需健壮）。"""
    try:
        schema = json.loads(json_schema_text)
    except (ValueError, TypeError):
        return _fail("契约不是合法 JSON")

    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError):
        return _fail("响应体不是 JSON，无法按契约校验")

    try:
        validate = fastjsonschema.compile(schema)
    except Exception as exc:  # fastjsonschema 编译错误类型多样，统一兜底
        return _fail(f"契约 schema 无效：{exc}")

    try:
        validate(body)
    except fastjsonschema.JsonSchemaValueException as exc:
        return _fail(exc.message, [exc.message])

    return {"passed": True, "message": "响应符合契约", "errors": []}

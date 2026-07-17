"""更新 Swagger / 导入 · 对畸形 OpenAPI 文档的健壮性（避免解析异常变 500）。

回归：这些畸形输入过去会抛 AttributeError/TypeError → 路由 500「服务器内部错误」；
应改为要么友好 ValueError（→400），要么跳过坏项照常解析。
"""

import pytest

from app.services.apifox import import_service as svc


# ---------- validate_openapi：非 dict 文档 ----------
def test_validate_openapi_rejects_non_dict_doc():
    with pytest.raises(ValueError):
        svc.validate_openapi(["not", "a", "dict"])  # 过去 doc.get → AttributeError


# ---------- parse_openapi：parameters 含非 dict 项 ----------
def test_parse_openapi_skips_non_dict_param():
    doc = {
        "openapi": "3.0.0",
        "paths": {"/x": {"get": {"parameters": ["坏参数", 123], "responses": {}}}},
    }

    eps = svc.parse_openapi(doc)  # 过去 param.get(...) → AttributeError

    assert len(eps) == 1 and eps[0]["method"] == "GET"


def test_parse_openapi_handles_non_list_parameters():
    doc = {
        "openapi": "3.0.0",
        "paths": {"/x": {"parameters": {"bad": 1}, "get": {"responses": {}}}},
    }

    eps = svc.parse_openapi(doc)

    assert len(eps) == 1


# ---------- _body_spec：content 媒体项非 dict ----------
def test_parse_openapi_handles_malformed_request_body():
    doc = {
        "openapi": "3.0.0",
        "paths": {
            "/x": {
                "post": {
                    "requestBody": {"content": {"application/json": "不是对象"}},
                    "responses": {},
                }
            }
        },
    }

    eps = svc.parse_openapi(doc)  # 过去 media.get(...) → AttributeError

    assert len(eps) == 1 and eps[0]["method"] == "POST"


# ---------- 正常文档仍正确解析 ----------
def test_parse_openapi_normal_doc_still_works():
    doc = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "summary": "用户列表",
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer"}, "required": True}
                    ],
                    "responses": {},
                }
            }
        },
    }

    eps = svc.parse_openapi(doc)

    assert eps[0]["name"] == "用户列表"
    assert [r.key for r in eps[0]["request_spec"].query] == ["page"]

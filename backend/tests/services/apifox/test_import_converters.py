"""Apifox 导入 · 多格式归一化（Swagger 2.0 / Postman / cURL → OpenAPI 3.x）。

验证：格式识别分派、各转换器关键映射、转换后能被现有 parse_openapi 解析出接口。
"""

import json

import pytest

from app.services.apifox import import_converters as conv
from app.services.apifox import import_service


# ---------- 识别分派 ----------
def test_to_openapi3_passthrough_openapi3():
    doc = {"openapi": "3.0.0", "paths": {}}
    assert conv.to_openapi3(json.dumps(doc)) is not None


def test_to_openapi3_rejects_unknown():
    with pytest.raises(ValueError):
        conv.to_openapi3('{"foo": "bar"}')


def test_to_openapi3_rejects_empty():
    with pytest.raises(ValueError):
        conv.to_openapi3("   ")


# ---------- Swagger 2.0 ----------
SWAGGER2 = {
    "swagger": "2.0",
    "basePath": "/api/v1",
    "paths": {
        "/users": {
            "get": {"parameters": [{"name": "page", "in": "query", "type": "integer"}], "responses": {}},
            "post": {
                "parameters": [{"name": "body", "in": "body", "schema": {"$ref": "#/definitions/User"}}],
                "responses": {},
            },
        }
    },
    "definitions": {"User": {"type": "object", "properties": {"name": {"type": "string"}}}},
}


def test_swagger2_converts_and_parses():
    doc = conv.to_openapi3(json.dumps(SWAGGER2))

    assert doc["openapi"].startswith("3")
    assert "User" in doc["components"]["schemas"]  # definitions → components.schemas
    # body 参数 → requestBody，$ref 改写
    ref = doc["paths"]["/api/v1/users"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert ref == "#/components/schemas/User"

    eps = import_service.parse_openapi(doc)
    keys = {(e["method"], e["path"]) for e in eps}
    assert keys == {("GET", "/api/v1/users"), ("POST", "/api/v1/users")}  # basePath 前缀


# ---------- cURL ----------
def test_curl_converts_and_parses():
    text = (
        "curl -X POST 'https://api.example.com/v1/login?ref=web' "
        "-H 'Content-Type: application/json' -H 'Authorization: Bearer x' "
        "-d '{\"user\":\"a\"}'"
    )
    doc = conv.to_openapi3(text)

    eps = import_service.parse_openapi(doc)
    assert len(eps) == 1
    ep = eps[0]
    assert ep["method"] == "POST" and ep["path"] == "/v1/login"
    assert ep["request_spec"].body.type == "json"
    assert any(h.key == "Authorization" for h in ep["request_spec"].headers)
    assert any(q.key == "ref" for q in ep["request_spec"].query)


def test_curl_defaults_get_without_body():
    doc = conv.to_openapi3("curl https://api.x/ping")
    eps = import_service.parse_openapi(doc)
    assert eps[0]["method"] == "GET" and eps[0]["path"] == "/ping"


def test_curl_without_url_raises():
    with pytest.raises(ValueError):
        conv.to_openapi3("curl -X GET -H 'A: b'")


# ---------- Postman ----------
POSTMAN = {
    "info": {"name": "C", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/"},
    "item": [
        {
            "name": "分组",
            "item": [
                {
                    "name": "查用户",
                    "request": {
                        "method": "GET",
                        "url": {"raw": "https://api.x/users?page=1", "query": [{"key": "page", "value": "1"}]},
                        "header": [{"key": "X-Token", "value": "t"}],
                    },
                }
            ],
        },
        {
            "name": "建用户",
            "request": {"method": "POST", "url": "https://api.x/users", "body": {"mode": "raw", "raw": "{\"n\":1}"}},
        },
    ],
}


def test_postman_converts_and_parses():
    doc = conv.to_openapi3(json.dumps(POSTMAN))

    eps = {(e["method"], e["path"]): e for e in import_service.parse_openapi(doc)}
    assert set(eps) == {("GET", "/users"), ("POST", "/users")}
    get = eps[("GET", "/users")]
    assert any(q.key == "page" for q in get["request_spec"].query)
    assert any(h.key == "X-Token" for h in get["request_spec"].headers)
    assert get["folder"] == "分组"  # 文件夹名 → tag
    assert eps[("POST", "/users")]["request_spec"].body.type == "json"


def test_postman_empty_raises():
    with pytest.raises(ValueError):
        conv.to_openapi3(json.dumps({"info": {"name": "x"}, "item": []}))

"""Apifox 导入 · 多格式 → OpenAPI 3.x 归一化。

各格式(Swagger 2.0 / Postman Collection / cURL)转成 OpenAPI 3.x 文档，交给现有
import_service 的 validate/parse/import 下游统一处理（下游不感知源格式）。
"""

import json
import shlex
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlparse

_HTTP_METHODS = ("get", "post", "put", "delete", "patch", "head", "options")


def to_openapi3(raw: str) -> Dict[str, Any]:
    """识别导入内容格式并归一化为 OpenAPI 3.x 文档；无法识别抛 ValueError。"""
    text = (raw or "").strip()
    if not text:
        raise ValueError("导入内容为空")

    doc: Any = None
    try:
        doc = json.loads(text)
    except (ValueError, TypeError):
        doc = None

    if isinstance(doc, dict):
        if str(doc.get("openapi") or "").startswith("3"):
            return doc  # 已是 OpenAPI 3.x
        if str(doc.get("swagger") or "") == "2.0":
            return swagger2_to_openapi3(doc)
        if isinstance(doc.get("info"), dict) and "item" in doc:
            return postman_to_openapi3(doc)
        raise ValueError("无法识别的 JSON（需 OpenAPI 3.x / Swagger 2.0 / Postman Collection）")

    if text.lower().startswith("curl"):
        return curl_to_openapi3(text)

    raise ValueError("无法识别的导入内容（支持 OpenAPI/Swagger JSON、Postman Collection、cURL）")


# ---------- Swagger 2.0 ----------
def swagger2_to_openapi3(doc: Dict[str, Any]) -> Dict[str, Any]:
    base = str(doc.get("basePath") or "").rstrip("/")
    out: Dict[str, Any] = {
        "openapi": "3.0.0",
        "info": doc.get("info") if isinstance(doc.get("info"), dict) else {"title": "Swagger 导入"},
        "paths": {},
        "components": {"schemas": doc.get("definitions") or {}},
    }
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        common = item.get("parameters") or []
        new_item: Dict[str, Any] = {}
        for method, op in item.items():
            if method not in _HTTP_METHODS or not isinstance(op, dict):
                continue
            params = [p for p in (list(common) + list(op.get("parameters") or [])) if isinstance(p, dict)]
            body = next((p for p in params if p.get("in") == "body"), None)
            new_op = {k: v for k, v in op.items() if k != "parameters"}
            new_op["parameters"] = [p for p in params if p.get("in") != "body"]
            if body and isinstance(body.get("schema"), dict):
                new_op["requestBody"] = {"content": {"application/json": {"schema": body["schema"]}}}
            new_item[method] = new_op
        out["paths"][(base + path) if base else path] = new_item
    # #/definitions/X → #/components/schemas/X（含内嵌 $ref，字符串替换安全）
    return json.loads(json.dumps(out, ensure_ascii=False).replace("#/definitions/", "#/components/schemas/"))


# ---------- Postman Collection v2 ----------
def _postman_path(raw_url: Any) -> Tuple[str, str]:
    """从 Postman url（字符串或对象）取 (path, raw)。保留 {{var}} 占位。"""
    raw = raw_url if isinstance(raw_url, str) else str((raw_url or {}).get("raw") or "")
    parsed = urlparse(raw)
    path = parsed.path or (raw if not parsed.scheme else "/")
    return (path or "/"), raw


def _header_params(headers: Any) -> List[Dict[str, Any]]:
    rows = []
    for h in headers or []:
        if isinstance(h, dict) and h.get("key") and not h.get("disabled"):
            rows.append({"name": h["key"], "in": "header", "schema": {"type": "string"},
                         "example": str(h.get("value") or "")})
    return rows


def _maybe_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text


def postman_to_openapi3(doc: Dict[str, Any]) -> Dict[str, Any]:
    paths: Dict[str, Any] = {}

    def walk(items: Any, folder: Optional[str]) -> None:
        for it in items or []:
            if not isinstance(it, dict):
                continue
            if "item" in it:  # 文件夹
                walk(it.get("item"), it.get("name") or folder)
                continue
            req = it.get("request")
            if not isinstance(req, dict):
                continue
            method = str(req.get("method") or "GET").lower()
            if method not in _HTTP_METHODS:
                continue
            path, raw = _postman_path(req.get("url"))
            op: Dict[str, Any] = {
                "summary": it.get("name") or raw,
                "tags": [folder] if folder else [],
                "parameters": _header_params(req.get("header")),
                "responses": {},
            }
            url_obj = req.get("url")
            if isinstance(url_obj, dict):
                for q in url_obj.get("query") or []:
                    if isinstance(q, dict) and q.get("key") and not q.get("disabled"):
                        op["parameters"].append({"name": q["key"], "in": "query",
                                                 "schema": {"type": "string"}, "example": str(q.get("value") or "")})
            body = req.get("body") or {}
            if isinstance(body, dict) and body.get("mode") == "raw" and body.get("raw"):
                op["requestBody"] = {"content": {"application/json": {"example": _maybe_json(body["raw"])}}}
            paths.setdefault(path, {})[method] = op

    walk(doc.get("item"), None)
    if not paths:
        raise ValueError("Postman Collection 中未找到可导入的请求")
    return {
        "openapi": "3.0.0",
        "info": doc.get("info") if isinstance(doc.get("info"), dict) else {"title": "Postman 导入"},
        "paths": paths,
    }


# ---------- cURL ----------
_CURL_VALUE_FLAGS = {"-u", "--user", "-o", "--output", "-A", "--user-agent", "-e", "--referer",
                     "--connect-timeout", "-m", "--max-time", "--cacert", "--cert", "--key"}


def _parse_curl(text: str) -> Dict[str, Any]:
    tokens = shlex.split(text.replace("\\\n", " "))
    method: Optional[str] = None
    url: Optional[str] = None
    headers: List[Tuple[str, str]] = []
    body: Optional[str] = None
    i = 1 if tokens and tokens[0] == "curl" else 0
    while i < len(tokens):
        tok = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if tok in ("-X", "--request") and nxt is not None:
            method = nxt.upper()
            i += 2
        elif tok in ("-H", "--header") and nxt is not None:
            if ":" in nxt:
                k, v = nxt.split(":", 1)
                headers.append((k.strip(), v.strip()))
            i += 2
        elif tok in ("-d", "--data", "--data-raw", "--data-binary", "--data-ascii") and nxt is not None:
            body = nxt
            i += 2
        elif tok == "--url" and nxt is not None:
            url = nxt
            i += 2
        elif tok in _CURL_VALUE_FLAGS and nxt is not None:
            i += 2
        elif tok.startswith("http://") or tok.startswith("https://"):
            url = tok
            i += 1
        else:
            i += 1
    if not url:
        raise ValueError("cURL 中未找到 URL")
    if not method:
        method = "POST" if body else "GET"
    return {"method": method, "url": url, "headers": headers, "body": body}


def curl_to_openapi3(text: str) -> Dict[str, Any]:
    parsed = _parse_curl(text)
    u = urlparse(parsed["url"])
    path = u.path or "/"
    op: Dict[str, Any] = {
        "summary": f"{parsed['method']} {path}",
        "parameters": [],
        "responses": {},
    }
    for k, v in parsed["headers"]:
        op["parameters"].append({"name": k, "in": "header", "schema": {"type": "string"}, "example": v})
    for qk, qv in parse_qsl(u.query):
        op["parameters"].append({"name": qk, "in": "query", "schema": {"type": "string"}, "example": qv})
    if parsed["body"]:
        op["requestBody"] = {"content": {"application/json": {"example": _maybe_json(parsed["body"])}}}
    return {
        "openapi": "3.0.0",
        "info": {"title": "cURL 导入"},
        "paths": {path: {parsed["method"].lower(): op}},
    }

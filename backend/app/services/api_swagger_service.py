import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
import yaml

HTTP_METHODS = ("get", "post", "put", "delete", "patch", "head", "options")
DEFAULT_ASSERTIONS = json.dumps([{"type": "status_code", "expected": 200}], ensure_ascii=False)


def _schema_to_example(schema: Optional[Dict[str, Any]], doc: Optional[Dict[str, Any]] = None) -> Any:
    if not schema:
        return None
    if "$ref" in schema and doc:
        ref = schema["$ref"]
        if ref.startswith("#/"):
            node: Any = doc
            for part in ref[2:].split("/"):
                if isinstance(node, dict):
                    node = node.get(part)
                else:
                    node = None
                    break
            if isinstance(node, dict):
                return _schema_to_example(node, doc)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        result: Dict[str, Any] = {}
        required = set(schema.get("required") or [])
        for key, prop in (schema.get("properties") or {}).items():
            if required and key not in required:
                continue
            value = _schema_to_example(prop, doc)
            if value is not None:
                result[key] = value
        return result
    if schema_type == "array":
        items = _schema_to_example(schema.get("items") or {}, doc)
        return [items] if items is not None else []
    if schema_type == "string":
        return schema.get("enum", ["string"])[0] if schema.get("enum") else "string"
    if schema_type == "integer":
        return 0
    if schema_type == "number":
        return 0
    if schema_type == "boolean":
        return False
    return None


def _resolve_base_url(doc: Dict[str, Any], override: Optional[str] = None) -> str:
    if override and override.strip():
        return override.strip().rstrip("/")
    if doc.get("openapi"):
        servers = doc.get("servers") or []
        if servers:
            url = str(servers[0].get("url") or "").strip()
            if url:
                return url.rstrip("/")
    if doc.get("swagger") == "2.0" or ("swagger" in doc and "paths" in doc):
        host = str(doc.get("host") or "").strip()
        base_path = str(doc.get("basePath") or "").strip()
        if not base_path.startswith("/"):
            base_path = f"/{base_path}" if base_path else ""
        schemes = doc.get("schemes") or ["https"]
        scheme = str(schemes[0]).strip() if schemes else "https"
        if host:
            return f"{scheme}://{host}{base_path}".rstrip("/")
    return ""


def _build_operation_name(method: str, path: str, operation: Dict[str, Any]) -> str:
    for key in ("summary", "operationId"):
        value = operation.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    pathname = path.split("?")[0] or "/"
    return f"{method.upper()} {pathname}"


def _extract_body_and_headers(
    doc: Dict[str, Any],
    operation: Dict[str, Any],
    is_swagger2: bool,
) -> Tuple[str, Dict[str, str]]:
    headers: Dict[str, str] = {}
    body = ""

    if is_swagger2:
        for param in operation.get("parameters") or []:
            if param.get("in") == "body":
                schema = param.get("schema") or {}
                example = param.get("example")
                if example is None:
                    example = _schema_to_example(schema, doc)
                if example is not None:
                    body = json.dumps(example, ensure_ascii=False, indent=2)
                    headers["Content-Type"] = "application/json"
                break
        consumes = operation.get("consumes") or doc.get("consumes") or []
        if consumes and not body:
            headers.setdefault("Content-Type", consumes[0])
        return body, headers

    request_body = operation.get("requestBody") or {}
    if not request_body:
        return body, headers
    content = request_body.get("content") or {}
    preferred = None
    for mime in ("application/json", "application/*+json", "*/*"):
        if mime in content:
            preferred = content[mime]
            headers["Content-Type"] = "application/json" if "json" in mime else mime
            break
    if preferred is None and content:
        mime, preferred = next(iter(content.items()))
        headers["Content-Type"] = mime
    if not preferred:
        return body, headers
    example = preferred.get("example")
    if example is None and preferred.get("examples"):
        first_example = next(iter(preferred["examples"].values()))
        if isinstance(first_example, dict):
            example = first_example.get("value")
    if example is None:
        example = _schema_to_example(preferred.get("schema") or {}, doc)
    if example is not None:
        body = json.dumps(example, ensure_ascii=False, indent=2)
    return body, headers


def _normalize_path(path: str, base_url: str) -> Tuple[str, str, str]:
    if path.startswith("http://") or path.startswith("https://"):
        parsed = urlparse(path)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return path, base.rstrip("/"), parsed.path or "/"
    normalized_path = path if path.startswith("/") else f"/{path}"
    full_url = urljoin(f"{base_url.rstrip('/')}/", normalized_path.lstrip("/")) if base_url else normalized_path
    return full_url, base_url.rstrip("/"), normalized_path


def parse_swagger_document(
    doc: Dict[str, Any],
    *,
    base_url_override: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not isinstance(doc, dict):
        raise ValueError("Swagger 文档格式无效")
    if "paths" not in doc:
        raise ValueError("未找到 paths 节点，请确认 Swagger/OpenAPI 文档是否完整")

    is_swagger2 = str(doc.get("swagger", "")).startswith("2")
    base_url = _resolve_base_url(doc, base_url_override)
    results: List[Dict[str, Any]] = []

    for path, path_item in (doc.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        shared_params = path_item.get("parameters") or []
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            merged = dict(operation)
            if shared_params:
                merged["parameters"] = shared_params + (operation.get("parameters") or [])
            body, headers = _extract_body_and_headers(doc, merged, is_swagger2)
            full_url, resolved_base, normalized_path = _normalize_path(path, base_url)
            results.append(
                {
                    "name": _build_operation_name(method, path, operation),
                    "method": method.upper(),
                    "path": normalized_path,
                    "base_url": resolved_base,
                    "headers": json.dumps(headers, ensure_ascii=False, indent=2) if headers else "",
                    "body": body,
                    "assertions": DEFAULT_ASSERTIONS,
                    "source": "swagger",
                    "full_url": full_url,
                }
            )
    if not results:
        raise ValueError("文档中未解析到任何 HTTP 接口")
    return results


def load_swagger_text(raw_text: str) -> Dict[str, Any]:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Swagger 内容不能为空")
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError("Swagger 内容不是有效的 JSON 或 YAML") from exc
    if not isinstance(data, dict):
        raise ValueError("Swagger 文档根节点必须是对象")
    return data


def fetch_swagger_text(url: str, timeout: float = 20.0) -> str:
    target = (url or "").strip()
    if not target:
        raise ValueError("Swagger URL 不能为空")
    if not re.match(r"^https?://", target, re.IGNORECASE):
        raise ValueError("Swagger URL 必须以 http:// 或 https:// 开头")
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(target)
            response.raise_for_status()
            return response.text
    except httpx.HTTPError as exc:
        raise ValueError(f"拉取 Swagger URL 失败: {exc}") from exc


def parse_swagger_source(
    *,
    source_type: str,
    raw_text: Optional[str] = None,
    swagger_url: Optional[str] = None,
    base_url_override: Optional[str] = None,
) -> List[Dict[str, Any]]:
    source = (source_type or "content").strip().lower()
    if source == "url":
        text = fetch_swagger_text(swagger_url or "")
    elif source in ("content", "swagger"):
        text = raw_text or ""
    else:
        raise ValueError("不支持的数据来源类型")
    doc = load_swagger_text(text)
    return parse_swagger_document(doc, base_url_override=base_url_override)

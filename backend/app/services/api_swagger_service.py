import json
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
import yaml

from app.services.api_request_builder import META_KEY

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


def _resolve_ref(doc: Dict[str, Any], node: Dict[str, Any]) -> Dict[str, Any]:
    ref = node.get("$ref")
    if not ref or not isinstance(ref, str) or not ref.startswith("#/"):
        return node
    current: Any = doc
    for part in ref[2:].split("/"):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return node
    return current if isinstance(current, dict) else node


def _schema_property_names(schema: Optional[Dict[str, Any]], doc: Optional[Dict[str, Any]] = None) -> List[str]:
    if not schema:
        return []
    if "$ref" in schema and doc:
        schema = _resolve_ref(doc, schema)
    if not isinstance(schema, dict):
        return []
    props = schema.get("properties") or {}
    if isinstance(props, dict) and props:
        return list(props.keys())
    schema_type = schema.get("type")
    if schema_type == "array":
        item_schema = schema.get("items") or {}
        if "$ref" in item_schema and doc:
            item_schema = _resolve_ref(doc, item_schema)
        return _schema_property_names(item_schema, doc)
    return []


def _extract_input_params_summary(
    doc: Dict[str, Any],
    operation: Dict[str, Any],
    path: str,
    is_swagger2: bool,
    body: str,
) -> str:
    parts: List[str] = []
    path_vars = re.findall(r"\{([^}]+)\}", path)
    if path_vars:
        parts.append(f"path: {', '.join(dict.fromkeys(path_vars))}")

    query_names: List[str] = []
    header_names: List[str] = []
    form_names: List[str] = []

    for raw_param in operation.get("parameters") or []:
        if not isinstance(raw_param, dict):
            continue
        param = _resolve_ref(doc, raw_param)
        name = str(param.get("name") or "").strip()
        location = str(param.get("in") or "").strip()
        if not name:
            continue
        if location == "query":
            query_names.append(name)
        elif location == "path" and name not in path_vars:
            path_vars.append(name)
        elif location == "header" and name.lower() not in {"content-type", "accept"}:
            header_names.append(name)
        elif location in {"formData", "form-data"}:
            form_names.append(name)
        elif location == "body" and is_swagger2:
            schema = param.get("schema") or {}
            names = _schema_property_names(schema, doc)
            if names:
                parts.append(f"body: {', '.join(names[:8])}{'...' if len(names) > 8 else ''}")
            else:
                parts.append("body: *")

    if path_vars:
        parts = [f"path: {', '.join(dict.fromkeys(path_vars))}"] + [p for p in parts if not p.startswith("path:")]

    if query_names:
        parts.append(f"query: {', '.join(dict.fromkeys(query_names))}")
    if header_names:
        parts.append(f"header: {', '.join(dict.fromkeys(header_names))}")
    if form_names:
        parts.append(f"form: {', '.join(dict.fromkeys(form_names))}")

    body_names: List[str] = []
    if body:
        try:
            body_obj = json.loads(body)
            if isinstance(body_obj, dict) and body_obj:
                body_names = list(body_obj.keys())
            elif body_obj is not None:
                body_names = ["*"]
        except json.JSONDecodeError:
            body_names = ["raw"]
    elif not is_swagger2:
        request_body = operation.get("requestBody") or {}
        if isinstance(request_body, dict) and "$ref" in request_body:
            request_body = _resolve_ref(doc, request_body)
        content = (request_body or {}).get("content") or {}
        preferred = None
        for mime in ("application/json", "application/*+json", "*/*"):
            if mime in content:
                preferred = content[mime]
                break
        if preferred is None and content:
            preferred = next(iter(content.values()))
        if isinstance(preferred, dict):
            body_names = _schema_property_names(preferred.get("schema") or {}, doc)

    if body_names and not any(part.startswith("body:") for part in parts):
        shown = body_names[:8]
        suffix = "..." if len(body_names) > 8 else ""
        parts.append(f"body: {', '.join(shown)}{suffix}")

    return "; ".join(parts) if parts else "-"


def _extract_param_lists(
    doc: Dict[str, Any],
    operation: Dict[str, Any],
    path: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    query_rows: List[Dict[str, Any]] = []
    path_rows: List[Dict[str, Any]] = []
    seen_query: set[str] = set()
    seen_path: set[str] = set()

    for name in re.findall(r"\{([^}]+)\}", path):
        if name not in seen_path:
            seen_path.add(name)
            path_rows.append({"key": name, "value": "", "enabled": True})

    for raw_param in operation.get("parameters") or []:
        if not isinstance(raw_param, dict):
            continue
        param = _resolve_ref(doc, raw_param)
        name = str(param.get("name") or "").strip()
        location = str(param.get("in") or "").strip()
        if not name:
            continue
        if location == "query" and name not in seen_query:
            seen_query.add(name)
            query_rows.append({"key": name, "value": "", "enabled": True})
        elif location == "path" and name not in seen_path:
            seen_path.add(name)
            path_rows.append({"key": name, "value": "", "enabled": True})

    return query_rows, path_rows


def _format_input_params_display(
    query_params: List[Dict[str, Any]],
    path_params: List[Dict[str, Any]],
    body: str,
) -> str:
    parts: List[str] = []
    path_items = [row for row in path_params if str(row.get("key") or "").strip()]
    if path_items:
        parts.append(
            "path: "
            + ", ".join(
                f"{row['key']}={row.get('value') or '?'}" for row in path_items[:6]
            )
        )
    query_items = [row for row in query_params if str(row.get("key") or "").strip()]
    if query_items:
        parts.append(
            "query: "
            + ", ".join(
                f"{row['key']}={row.get('value') or '?'}" for row in query_items[:6]
            )
        )
    if body and str(body).strip():
        try:
            parsed = json.loads(body)
            preview = json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            preview = str(body).strip()
        if len(preview) > 72:
            preview = preview[:69] + "..."
        parts.append(f"body: {preview}")
    return "; ".join(parts) if parts else "-"


def _build_case_headers(
    headers: Dict[str, str],
    query_params: List[Dict[str, Any]],
    path_params: List[Dict[str, Any]],
    body: str,
) -> str:
    raw = dict(headers or {})
    body_text = (body or "").strip()
    if body_text.startswith("{") or body_text.startswith("["):
        body_type = "json"
    elif body_text:
        body_type = "raw"
    else:
        body_type = "none"
    meta: Dict[str, Any] = {
        "body_type": body_type,
        "query": query_params,
        "path_vars": path_params,
    }
    if body_type == "json" and body_text:
        meta["body_stores"] = {"json": body}
    raw[META_KEY] = meta
    return json.dumps(raw, ensure_ascii=False, indent=2)


def apply_generated_to_swagger_item(item: Dict[str, Any], generated: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(item)
    query_params = [dict(row) for row in (result.get("query_params") or [])]
    path_params = [dict(row) for row in (result.get("path_params") or [])]

    new_body = generated.get("body")
    if new_body:
        result["body"] = new_body

    query_map = generated.get("query") if isinstance(generated.get("query"), dict) else {}
    for row in query_params:
        key = str(row.get("key") or "").strip()
        if key and key in query_map:
            row["value"] = str(query_map[key])

    path_map = generated.get("path") if isinstance(generated.get("path"), dict) else {}
    for row in path_params:
        key = str(row.get("key") or "").strip()
        if key and key in path_map:
            row["value"] = str(path_map[key])

    result["query_params"] = query_params
    result["path_params"] = path_params

    headers_obj: Dict[str, str] = {}
    if result.get("headers"):
        try:
            parsed_headers = json.loads(result["headers"])
            if isinstance(parsed_headers, dict):
                headers_obj = {
                    str(key): str(value)
                    for key, value in parsed_headers.items()
                    if key != META_KEY
                }
        except json.JSONDecodeError:
            headers_obj = {}

    result["headers"] = _build_case_headers(
        headers_obj,
        query_params,
        path_params,
        result.get("body") or "",
    )
    result["input_params"] = _format_input_params_display(
        query_params,
        path_params,
        result.get("body") or "",
    )
    return result


def _parse_input_params_segment(segment: str) -> Tuple[str, List[str]]:
    text = (segment or "").strip()
    if not text or ":" not in text:
        return "", []
    kind, raw_values = text.split(":", 1)
    kind = kind.strip().lower()
    values = [item.strip() for item in raw_values.split(",") if item.strip()]
    return kind, values


def prepare_swagger_item_for_generate(item: Dict[str, Any]) -> Dict[str, Any]:
    prepared = dict(item)
    query_params = [dict(row) for row in (prepared.get("query_params") or []) if isinstance(row, dict)]
    path_params = [dict(row) for row in (prepared.get("path_params") or []) if isinstance(row, dict)]
    has_body = bool((prepared.get("body") or "").strip())
    has_query = any(str(row.get("key") or "").strip() for row in query_params)
    has_path = any(str(row.get("key") or "").strip() for row in path_params)
    if has_body or has_query or has_path:
        prepared["query_params"] = query_params
        prepared["path_params"] = path_params
        return prepared

    input_params = str(prepared.get("input_params") or "").strip()
    if not input_params or input_params == "-":
        prepared["query_params"] = query_params
        prepared["path_params"] = path_params
        return prepared

    body_fields: List[str] = []
    for segment in input_params.split(";"):
        kind, values = _parse_input_params_segment(segment)
        if not kind or not values:
            continue
        if kind == "body":
            if values[0].startswith("{") or values[0].startswith("["):
                continue
            body_fields = values
        elif kind == "query":
            for name in values:
                if name.endswith("=?") or "=" in name:
                    name = name.split("=", 1)[0].strip()
                if name and not any(row.get("key") == name for row in query_params):
                    query_params.append({"key": name, "value": "", "enabled": True})
        elif kind == "path":
            for name in values:
                if name.endswith("=?") or "=" in name:
                    name = name.split("=", 1)[0].strip()
                if name and not any(row.get("key") == name for row in path_params):
                    path_params.append({"key": name, "value": "", "enabled": True})

    if body_fields and not has_body:
        prepared["body"] = json.dumps(
            {field: "string" for field in body_fields},
            ensure_ascii=False,
            indent=2,
        )

    prepared["query_params"] = query_params
    prepared["path_params"] = path_params
    return prepared


def swagger_item_has_generatable_params(item: Dict[str, Any]) -> bool:
    prepared = prepare_swagger_item_for_generate(item)
    if (prepared.get("body") or "").strip():
        return True
    if any(str(row.get("key") or "").strip() for row in prepared.get("query_params") or []):
        return True
    if any(str(row.get("key") or "").strip() for row in prepared.get("path_params") or []):
        return True
    return False


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
    if isinstance(request_body, dict) and "$ref" in request_body:
        request_body = _resolve_ref(doc, request_body)
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
        schema = preferred.get("schema") or {}
        if isinstance(schema, dict) and "$ref" in schema:
            schema = _resolve_ref(doc, schema)
        example = _schema_to_example(schema, doc)
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
            query_params, path_params = _extract_param_lists(doc, merged, path)
            input_params = _extract_input_params_summary(doc, merged, path, is_swagger2, body)
            case_headers = _build_case_headers(headers, query_params, path_params, body)
            results.append(
                {
                    "name": _build_operation_name(method, path, operation),
                    "method": method.upper(),
                    "path": normalized_path,
                    "base_url": resolved_base,
                    "headers": case_headers,
                    "body": body,
                    "input_params": input_params,
                    "query_params": query_params,
                    "path_params": path_params,
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

import json
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.services.api_json_path import resolve_json_path
from app.services.api_variable_service import normalize_scope

VALID_EXTRACT_SOURCES = frozenset({
    "response_json",
    "response_xml",
    "response_text",
    "response_header",
    "response_cookie",
    "response_time",
    "request_header",
    "request_body",
})

LEGACY_SOURCE_MAP = {
    "body": "response_json",
    "header": "response_header",
}

SOURCE_LABELS = {
    "response_json": "Response JSON",
    "response_xml": "Response XML",
    "response_text": "Response Text",
    "response_header": "Response Header",
    "response_cookie": "Response Cookie",
    "response_time": "响应时间",
    "request_header": "Request Header",
    "request_body": "Request Body",
}


def normalize_extract_source(source: Optional[str]) -> str:
    normalized = (source or "response_json").lower().strip()
    normalized = LEGACY_SOURCE_MAP.get(normalized, normalized)
    return normalized if normalized in VALID_EXTRACT_SOURCES else "response_json"


def stringify_extract_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _lookup_header(headers: Dict[str, Any], name: str) -> Optional[str]:
    if not name:
        return None
    for key, value in headers.items():
        if str(key).lower() == name.lower():
            return str(value)
    return None


def _extract_response_json(response: httpx.Response, path: str) -> Tuple[bool, str, str]:
    if not path:
        return False, "", "未填写 JSON Path"
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return False, "", "响应不是合法 JSON"
    found, actual = resolve_json_path(payload, path)
    if not found:
        return False, "", f"路径 {path} 在响应中不存在"
    return True, stringify_extract_value(actual), ""


def _extract_request_body(request: Dict[str, Any], path: str) -> Tuple[bool, str, str]:
    body = str(request.get("body") or "")
    if not path:
        return True, body, ""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False, "", "请求体不是合法 JSON，无法使用 JSON Path"
    found, actual = resolve_json_path(payload, path)
    if not found:
        return False, "", f"路径 {path} 在请求体中不存在"
    return True, stringify_extract_value(actual), ""


def _extract_response_xml(response: httpx.Response, path: str) -> Tuple[bool, str, str]:
    text = response.text or ""
    if not text.strip():
        return False, "", "响应体为空"
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return False, "", "响应不是合法 XML"
    if not path:
        return True, text, ""
    query = path.strip()
    if query.startswith("//"):
        node = root.find(query)
    elif query.startswith("/"):
        node = root.find(f".{query}")
    else:
        node = root.find(f".//{query}")
    if node is None:
        return False, "", f"XML 路径 {path} 未匹配到节点"
    value = (node.text or "").strip()
    if not value and len(node):
        value = ET.tostring(node, encoding="unicode")
    return True, value, ""


def _extract_response_text(response: httpx.Response, path: str) -> Tuple[bool, str, str]:
    text = response.text or ""
    if not path:
        return True, text, ""
    if path.startswith("regex:"):
        pattern = path[6:]
        if not pattern:
            return False, "", "正则表达式为空"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return False, "", f"正则 {pattern} 未匹配"
        return True, match.group(1) if match.groups() else match.group(0), ""
    return True, text, ""


def _extract_value_by_source(
    source: str,
    path: str,
    response: httpx.Response,
    request: Optional[Dict[str, Any]],
    duration_ms: float,
) -> Tuple[bool, str, str]:
    request = request or {}

    if source == "response_json":
        return _extract_response_json(response, path)
    if source == "response_header":
        if not path:
            return False, "", "未填写响应头名称"
        value = _lookup_header(dict(response.headers), path)
        if value is None:
            return False, "", f"响应头 {path} 不存在"
        return True, value, ""
    if source == "response_cookie":
        if not path:
            return False, "", "未填写 Cookie 名称"
        value = response.cookies.get(path)
        if value is None:
            return False, "", f"Cookie {path} 不存在"
        return True, str(value), ""
    if source == "response_time":
        return True, str(int(round(duration_ms))), ""
    if source == "response_text":
        return _extract_response_text(response, path)
    if source == "response_xml":
        return _extract_response_xml(response, path)
    if source == "request_header":
        if not path:
            return False, "", "未填写请求头名称"
        headers = request.get("headers") or {}
        value = _lookup_header(headers, path)
        if value is None:
            return False, "", f"请求头 {path} 不存在"
        return True, value, ""
    if source == "request_body":
        return _extract_request_body(request, path)
    return False, "", f"未知提取来源 {source}"


def apply_response_extractors(
    extractors: List[Dict[str, Any]],
    response: httpx.Response,
    request: Optional[Dict[str, Any]] = None,
    duration_ms: float = 0,
) -> Tuple[Dict[str, str], List[Dict[str, str]], List[Dict[str, Any]]]:
    extracted: Dict[str, str] = {}
    scoped_items: List[Dict[str, str]] = []
    results: List[Dict[str, Any]] = []

    for item in extractors or []:
        if not item.get("enabled", True):
            continue
        key = (item.get("key") or "").strip()
        if not key:
            continue

        source = normalize_extract_source(item.get("source"))
        path = (item.get("path") or "").strip()
        scope = normalize_scope(item.get("scope"))
        source_label = SOURCE_LABELS.get(source, source)
        scope_label = {"temporary": "临时变量", "environment": "环境变量", "global": "全局变量"}.get(scope, scope)
        result = {
            "type": "extract",
            "passed": False,
            "expected": key,
            "actual": None,
            "message": "",
            "scope": scope,
            "source": source,
        }

        try:
            ok, text_value, error_message = _extract_value_by_source(
                source,
                path,
                response,
                request,
                duration_ms,
            )
            if not ok:
                result["message"] = f"提取 {key} 失败：{error_message}"
                results.append(result)
                continue

            extracted[key] = text_value
            scoped_items.append({"key": key, "value": text_value, "scope": scope})
            result["passed"] = True
            result["actual"] = text_value
            result["message"] = f"从{source_label}提取{scope_label} {key} = {text_value}"
        except Exception as exc:
            result["message"] = f"提取 {key} 失败：{exc}"

        results.append(result)

    return extracted, scoped_items, results

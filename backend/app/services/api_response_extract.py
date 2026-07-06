import json
from typing import Any, Dict, List, Tuple

import httpx

from app.services.api_json_path import resolve_json_path
from app.services.api_variable_service import normalize_scope


def stringify_extract_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def apply_response_extractors(
    extractors: List[Dict[str, Any]],
    response: httpx.Response,
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

        source = (item.get("source") or "body").lower()
        path = (item.get("path") or "").strip()
        scope = normalize_scope(item.get("scope"))
        result = {
            "type": "extract",
            "passed": False,
            "expected": key,
            "actual": None,
            "message": "",
            "scope": scope,
        }

        try:
            if source == "header":
                if not path:
                    result["message"] = f"提取 {key} 失败：未填写响应头名称"
                    results.append(result)
                    continue
                value = response.headers.get(path)
                if value is None:
                    result["message"] = f"提取 {key} 失败：响应头 {path} 不存在"
                    results.append(result)
                    continue
                text_value = str(value)
            elif source == "body":
                if not path:
                    result["message"] = f"提取 {key} 失败：未填写 JSON Path"
                    results.append(result)
                    continue
                try:
                    payload = response.json()
                except json.JSONDecodeError:
                    result["message"] = f"提取 {key} 失败：响应不是合法 JSON"
                    results.append(result)
                    continue
                found, actual = resolve_json_path(payload, path)
                if not found:
                    result["message"] = f"提取 {key} 失败：路径 {path} 在响应中不存在"
                    results.append(result)
                    continue
                text_value = stringify_extract_value(actual)
            else:
                result["message"] = f"提取 {key} 失败：未知来源 {source}"
                results.append(result)
                continue

            extracted[key] = text_value
            scoped_items.append({"key": key, "value": text_value, "scope": scope})
            result["passed"] = True
            result["actual"] = text_value
            scope_label = {"temporary": "临时变量", "environment": "环境变量", "global": "全局变量"}.get(scope, scope)
            result["message"] = f"提取{scope_label} {key} = {text_value}"
        except Exception as exc:
            result["message"] = f"提取 {key} 失败：{exc}"

        results.append(result)

    return extracted, scoped_items, results

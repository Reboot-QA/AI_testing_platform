import json
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.services.api_json_path import resolve_json_path


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
) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    extracted: Dict[str, str] = {}
    results: List[Dict[str, Any]] = []

    for item in extractors or []:
        if not item.get("enabled", True):
            continue
        key = (item.get("key") or "").strip()
        if not key:
            continue

        source = (item.get("source") or "body").lower()
        path = (item.get("path") or "").strip()
        result = {
            "type": "extract",
            "passed": False,
            "expected": key,
            "actual": None,
            "message": "",
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
            result["passed"] = True
            result["actual"] = text_value
            result["message"] = f"提取变量 {key} = {text_value}"
        except Exception as exc:
            result["message"] = f"提取 {key} 失败：{exc}"

        results.append(result)

    return extracted, results

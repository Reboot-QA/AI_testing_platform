"""Apifox 断言/JSON 路径助手。迁移自老 api_runner_service，被 run_engine 与老套件执行器共用。"""

import json
from typing import Any, Dict

import httpx


def _truncate_text(text: str, limit: int = 8000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... (truncated)"


def _extract_json_path(data: Any, path: str) -> Any:
    if not path:
        return data
    normalized = path.strip()
    if normalized.startswith("$."):
        normalized = normalized[2:]
    elif normalized.startswith("$"):
        normalized = normalized[1:].lstrip(".")
    current = data
    for part in normalized.replace("[", ".").replace("]", "").split("."):
        if not part:
            continue
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        else:
            return None
    return current


def _evaluate_assertion(
    assertion: Dict[str, Any],
    response: httpx.Response,
    duration_ms: float,
) -> Dict[str, Any]:
    assertion_type = assertion.get("type", "")
    result = {
        "type": assertion_type,
        "passed": False,
        "expected": assertion.get("expected"),
        "actual": None,
        "message": "",
    }

    if assertion_type == "status_code":
        expected: Any = int(assertion.get("expected", 200))
        actual: Any = response.status_code
        result["expected"] = expected
        result["actual"] = actual
        result["passed"] = actual == expected
        result["message"] = f"状态码 {actual} {'==' if result['passed'] else '!='} {expected}"
        return result

    if assertion_type == "response_time":
        max_ms = float(assertion.get("max_ms", assertion.get("expected", 3000)))
        result["expected"] = max_ms
        result["actual"] = duration_ms
        result["passed"] = duration_ms <= max_ms
        result["message"] = f"响应时间 {duration_ms:.0f}ms {'<=' if result['passed'] else '>'} {max_ms}ms"
        return result

    if assertion_type == "contains":
        expected = str(assertion.get("expected", ""))
        target = assertion.get("target", "body")
        if target == "headers":
            actual = json.dumps(dict(response.headers), ensure_ascii=False)
        else:
            actual = response.text
        result["expected"] = expected
        result["actual"] = _truncate_text(actual, 500)
        result["passed"] = expected in actual
        result["message"] = f"内容{'包含' if result['passed'] else '不包含'} \"{expected}\""
        return result

    if assertion_type == "header":
        header_name = assertion.get("name", "")
        expected = str(assertion.get("expected", ""))
        actual = response.headers.get(header_name, "")
        result["expected"] = expected
        result["actual"] = actual
        result["passed"] = actual == expected
        result["message"] = f"响应头 {header_name}: {actual} {'==' if result['passed'] else '!='} {expected}"
        return result

    if assertion_type == "json_path":
        path = assertion.get("path", "")
        expected = assertion.get("expected")
        try:
            payload = response.json()
        except json.JSONDecodeError:
            result["message"] = "响应不是合法 JSON"
            return result
        actual = _extract_json_path(payload, path)
        result["expected"] = expected
        result["actual"] = actual
        result["passed"] = actual == expected
        result["message"] = f"{path} = {actual} {'==' if result['passed'] else '!='} {expected}"
        return result

    result["message"] = f"未知断言类型: {assertion_type}"
    return result

import json
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.services.ai_service import _build_request_payload, _extract_llm_error

API_DATA_SYSTEM_PROMPT = """你是一位资深接口测试工程师。根据接口信息，为请求参数生成可直接用于调试的真实测试数据。

要求：
1. 必须替换所有占位符（如 "string"、0、false、空字符串），包括嵌套对象和数组内的字段
2. project_id 使用 1；username 使用 admin；password 使用 admin123
3. file 字段使用示例文件名，如 需求文档示例.txt
4. requirements/items 等数组至少生成 1 条完整对象，title/description 使用中文业务描述
5. 保持原有 JSON 结构与字段名不变，只替换值
6. 只输出 JSON 对象，格式如下：
{
  "body": <JSON对象>,
  "query": {"参数名": "参数值"},
  "path": {"变量名": "变量值"}
}
若无 query/path 参数则返回空对象 {}。
不要输出 markdown 代码块或其它说明文字。"""

LIST_OBJECT_KEYS = {
    "requirements",
    "items",
    "records",
    "list",
    "cases",
    "data",
    "rows",
    "entries",
}


def _infer_body_type(body: Optional[str]) -> str:
    text = (body or "").strip()
    if not text:
        return "none"
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and parsed and all(isinstance(item, dict) and "key" in item for item in parsed):
            return "form-data"
    except json.JSONDecodeError:
        pass
    if text.startswith("{") or text.startswith("["):
        return "json"
    return "raw"


def _normalize_body_type(body_type: str, body: Optional[str]) -> str:
    normalized = (body_type or "none").strip().lower()
    if body and body.strip() and normalized in {"none", ""}:
        return _infer_body_type(body)
    return normalized or "none"


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return text in {"", "string", "str", "text", "example", "sample", "null", "undefined"}
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 0
    return False


def _guess_value(key: str, value: Any, fake: Any, *, force: bool = False) -> Any:
    if isinstance(value, dict):
        return {
            child_key: _guess_value(child_key, child_value, fake, force=force)
            for child_key, child_value in value.items()
        }

    if isinstance(value, list):
        key_lower = (key or "").lower()
        if not value:
            template: Any = "string"
            if key_lower in LIST_OBJECT_KEYS:
                template = {"title": "示例需求标题", "description": "示例需求描述"}
            return [_guess_value(key, template, fake, force=force)]
        first = value[0]
        generated = _guess_value(key, first, fake, force=force)
        if key_lower in LIST_OBJECT_KEYS and isinstance(first, dict) and isinstance(generated, dict):
            second = dict(generated)
            if "title" in second:
                second["title"] = fake.sentence(nb_words=5)
            return [generated, second]
        return [generated]

    if not force and not _is_placeholder(value):
        return value

    key_lower = (key or "").lower()
    if key_lower in {"project_id"} or key_lower.endswith("_project_id"):
        return 1
    if key_lower in {"file", "filename", "filepath", "document", "attachment"} or key_lower.endswith("_file"):
        return "需求文档示例.txt"
    if key_lower in {"provider_id", "suite_id", "case_id", "user_id", "requirement_id"}:
        return 1
    if "password" in key_lower or key_lower.endswith("pwd"):
        return "admin123"
    if any(token in key_lower for token in ("username", "account", "loginname", "user_name")):
        return "admin"
    if key_lower in {"user", "login"}:
        return "admin"
    if "email" in key_lower or key_lower.endswith("mail"):
        return "test@example.com"
    if any(token in key_lower for token in ("phone", "mobile", "tel")):
        return fake.phone_number()
    if "title" in key_lower or key_lower.endswith("_title"):
        return fake.sentence(nb_words=5)
    if any(token in key_lower for token in ("name", "nickname", "fullname", "full_name")):
        return fake.name()
    if any(token in key_lower for token in ("subject",)):
        return fake.sentence(nb_words=4)
    if any(token in key_lower for token in ("desc", "description", "remark", "comment", "content")):
        return fake.text(max_nb_chars=32)
    if any(token in key_lower for token in ("address", "addr")):
        return fake.address()
    if any(token in key_lower for token in ("city",)):
        return fake.city()
    if key_lower.endswith("_id") or key_lower == "id":
        return fake.random_int(min=1, max=9999)
    if any(token in key_lower for token in ("code", "no", "num")):
        return fake.random_int(min=1000, max=999999)
    if any(token in key_lower for token in ("amount", "price", "money", "fee")):
        return round(fake.random_number(digits=2, fix_len=False) / 100, 2)
    if any(token in key_lower for token in ("count", "qty", "quantity", "size", "page", "limit")):
        return fake.random_int(min=1, max=20)
    if any(token in key_lower for token in ("status", "type", "role", "gender", "sex")):
        return 1
    if any(token in key_lower for token in ("enabled", "active", "flag", "is")):
        return True
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return fake.random_int(min=1, max=100)
    if isinstance(value, float):
        return round(fake.pyfloat(min_value=1, max_value=100), 2)
    return fake.word()


def _fill_json_body(body: Optional[str], fake: Any) -> Optional[str]:
    if not body or not str(body).strip():
        return body
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        if _is_placeholder(body):
            return fake.text(max_nb_chars=64)
        return body
    filled = _guess_value("", parsed, fake, force=True)
    return json.dumps(filled, ensure_ascii=False, indent=2)


def _mock_generate_api_data(
    *,
    method: str,
    path: str,
    body: Optional[str],
    body_type: str,
    query_params: Optional[List[Dict[str, Any]]] = None,
    path_params: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    from faker import Faker

    fake = Faker("zh_CN")
    effective_type = _normalize_body_type(body_type, body)
    result: Dict[str, Any] = {"body": body, "query": {}, "path": {}}

    if body and str(body).strip():
        if effective_type in {"json", "none", "raw"}:
            result["body"] = _fill_json_body(body, fake)
        elif effective_type in {"form-data", "urlencoded"}:
            try:
                parsed = json.loads(body)
                if isinstance(parsed, list):
                    generated_rows = []
                    for row in parsed:
                        key = str(row.get("key") or "")
                        if not key:
                            generated_rows.append(row)
                            continue
                        current = row.get("value", "")
                        generated_rows.append(
                            {**row, "value": str(_guess_value(key, current, fake, force=True))}
                        )
                    result["body"] = json.dumps(generated_rows, ensure_ascii=False)
            except json.JSONDecodeError:
                result["body"] = body

    for row in query_params or []:
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        result["query"][key] = str(_guess_value(key, row.get("value", ""), fake, force=True))

    for row in path_params or []:
        key = str(row.get("key") or "").strip()
        if not key:
            continue
        result["path"][key] = str(_guess_value(key, row.get("value", ""), fake, force=True))

    return result


def _parse_api_data_response(content: str) -> Dict[str, Any]:
    text = (content or "").strip()
    if not text:
        raise ValueError("LLM 返回内容为空")

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("LLM 返回内容不是有效 JSON") from None
        data = json.loads(match.group())

    if not isinstance(data, dict):
        raise ValueError("LLM 返回格式不符合预期，需要 JSON 对象")

    body = data.get("body")
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False, indent=2)
    elif body is not None:
        body = str(body)

    query = data.get("query") if isinstance(data.get("query"), dict) else {}
    path = data.get("path") if isinstance(data.get("path"), dict) else {}
    return {"body": body, "query": query, "path": path}


def _post_process_generated(data: Dict[str, Any]) -> Dict[str, Any]:
    from faker import Faker

    fake = Faker("zh_CN")
    body = data.get("body")
    if body:
        data["body"] = _fill_json_body(body, fake)
    query = data.get("query") if isinstance(data.get("query"), dict) else {}
    path = data.get("path") if isinstance(data.get("path"), dict) else {}
    data["query"] = {
        key: str(_guess_value(str(key), value, fake, force=True))
        for key, value in query.items()
        if str(key).strip()
    }
    data["path"] = {
        key: str(_guess_value(str(key), value, fake, force=True))
        for key, value in path.items()
        if str(key).strip()
    }
    return data


def _build_user_prompt(
    *,
    name: Optional[str],
    method: str,
    path: str,
    url: Optional[str],
    body: Optional[str],
    body_type: str,
    headers: Optional[str],
    query_params: Optional[List[Dict[str, Any]]],
    path_params: Optional[List[Dict[str, Any]]],
) -> str:
    lines = [
        f"接口名称：{name or '未命名'}",
        f"HTTP 方法：{method.upper()}",
        f"路径：{path or '/'}",
    ]
    if url:
        lines.append(f"完整 URL：{url}")
    if headers and headers.strip() not in {"", "{}"}:
        lines.append(f"请求头：{headers}")
    if query_params:
        query_text = json.dumps(
            [{k: row.get(k) for k in ("key", "value")} for row in query_params if row.get("key")],
            ensure_ascii=False,
        )
        lines.append(f"Query 参数：{query_text}")
    if path_params:
        path_text = json.dumps(
            [{k: row.get(k) for k in ("key", "value")} for row in path_params if row.get("key")],
            ensure_ascii=False,
        )
        lines.append(f"Path 变量：{path_text}")
    lines.append(f"Body 类型：{_normalize_body_type(body_type, body)}")
    lines.append(f"当前 Body：{body or '(空)'}")
    lines.append("请将所有占位符替换为可直接发送的中文测试数据，不要保留 string 或 0。")
    return "\n".join(lines)


async def generate_api_request_data(
    *,
    name: Optional[str],
    method: str,
    path: str,
    url: Optional[str] = None,
    body: Optional[str] = None,
    body_type: str = "json",
    headers: Optional[str] = None,
    query_params: Optional[List[Dict[str, Any]]] = None,
    path_params: Optional[List[Dict[str, Any]]] = None,
    api_base: str,
    api_key: str,
    model: str,
    mock_mode: bool,
) -> Tuple[Dict[str, Any], str]:
    normalized_type = _normalize_body_type(body_type, body)
    if mock_mode:
        return _mock_generate_api_data(
            method=method,
            path=path,
            body=body,
            body_type=normalized_type,
            query_params=query_params,
            path_params=path_params,
        ), "mock"

    if not api_key:
        raise ValueError("当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式")

    user_prompt = _build_user_prompt(
        name=name,
        method=method,
        path=path,
        url=url,
        body=body,
        body_type=normalized_type,
        headers=headers,
        query_params=query_params,
        path_params=path_params,
    )
    timeout = httpx.Timeout(connect=15.0, read=90.0, write=15.0, pool=15.0)
    request_payload = _build_request_payload(
        model=model,
        api_base=api_base,
        system_prompt=API_DATA_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{api_base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=request_payload,
            )
            if response.status_code >= 400:
                raise ValueError(_extract_llm_error(response))

            payload = response.json()
            message = payload.get("choices", [{}])[0].get("message", {})
            content = message.get("content") or ""
            if not content.strip():
                raise ValueError("LLM 返回内容为空，请检查模型名称或 API 配置")
            parsed = _parse_api_data_response(content)
            return _post_process_generated(parsed), "llm"
    except httpx.TimeoutException as exc:
        raise ValueError("LLM 请求超时，请稍后重试或检查网络连接") from exc
    except httpx.HTTPError as exc:
        raise ValueError(f"LLM 网络请求失败: {exc}") from exc

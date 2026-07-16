import json
import re
import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx

from app.services.document_service import split_document_chunks

SYSTEM_PROMPT = """你是一位资深测试工程师。根据用户提供的需求描述，生成结构化测试用例。
每条用例必须包含：title、priority(P0/P1/P2/P3)、preconditions、steps、expected_results、tags。
steps、preconditions、expected_results、tags 必须是字符串（不要用 JSON 数组）；步骤请用「1. 2. 3.」编号写在同一个字符串里，换行分隔。
所有字段内容必须使用简体中文撰写，不要输出英文标题或英文步骤（priority 字段除外，仍使用 P0/P1/P2/P3）。
只输出 JSON，格式为 {"testcases":[{"title":"...","priority":"P0","preconditions":"...","steps":"...","expected_results":"...","tags":"..."}]}，不要包含 markdown 代码块或其他说明文字。"""

REQUIREMENT_EXTRACT_PROMPT = """你是一位资深需求分析师。请从用户提供的需求文档内容中提取独立的「需求点」。
每个需求点应清晰、可测试，包含：
- title: 简短标题（不超过50字，使用简体中文）
- description: 详细描述（使用简体中文）
- req_type: functional/api/performance/security 之一
- priority: P0/P1/P2/P3

只输出 JSON：{"requirements":[{"title":"...","description":"...","req_type":"functional","priority":"P1"}]}
不要 markdown 代码块或其它说明文字。"""

CASE_TYPE_LABELS = {
    "functional": "功能测试",
    "api": "接口测试",
    "performance": "性能测试",
    "security": "安全测试",
}


def _case_type_label(case_type: str) -> str:
    return CASE_TYPE_LABELS.get(case_type, case_type)


def _mock_cases(requirement_text: str, count: int, case_type: str) -> List[Dict]:
    summary = requirement_text[:30].replace("\n", " ") if requirement_text else "功能模块"
    templates = [
        {
            "title": f"验证{summary}正常流程",
            "priority": "P0",
            "preconditions": "用户已登录，系统处于正常状态",
            "steps": "1. 进入相关功能页面\n2. 输入合法数据\n3. 点击提交/确认",
            "expected_results": "操作成功，页面展示正确结果，数据保存无误",
            "tags": f"{case_type},正常流程,冒烟",
        },
        {
            "title": f"验证{summary}必填项校验",
            "priority": "P1",
            "preconditions": "用户已登录",
            "steps": "1. 进入功能页面\n2. 不填写必填项\n3. 点击提交",
            "expected_results": "系统提示必填项不能为空，不允许提交",
            "tags": f"{case_type},异常,校验",
        },
        {
            "title": f"验证{summary}边界值输入",
            "priority": "P1",
            "preconditions": "用户已登录",
            "steps": "1. 输入最小边界值并提交\n2. 输入最大边界值并提交\n3. 输入超出边界值",
            "expected_results": "边界内值正常处理，超出边界时给出明确错误提示",
            "tags": f"{case_type},边界值",
        },
        {
            "title": f"验证{summary}权限控制",
            "priority": "P1",
            "preconditions": "准备不同角色账号（管理员/普通用户）",
            "steps": "1. 使用无权限账号访问功能\n2. 使用有权限账号访问功能",
            "expected_results": "无权限账号被拒绝访问，有权限账号可正常操作",
            "tags": f"{case_type},权限,安全",
        },
        {
            "title": f"验证{summary}并发操作",
            "priority": "P2",
            "preconditions": "多用户账号可用",
            "steps": "1. 两个用户同时操作同一资源\n2. 观察系统响应",
            "expected_results": "数据一致性保持，无脏读或覆盖丢失",
            "tags": f"{case_type},并发",
        },
    ]
    return templates[:count]


def split_generation_batches(total: int, batch_size: int = 5) -> List[int]:
    batches: List[int] = []
    remaining = total
    while remaining > 0:
        current = min(batch_size, remaining)
        batches.append(current)
        remaining -= current
    return batches


def distribute_count(total: int, parts: int) -> List[int]:
    if parts <= 0:
        return [total]
    base, remainder = divmod(total, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]


def build_generation_tasks(
    requirements: List[Dict[str, Any]],
    manual_text: str,
    total_count: int,
) -> List[Dict[str, Any]]:
    if requirements:
        counts = distribute_count(total_count, len(requirements))
        tasks: List[Dict[str, Any]] = []
        for req, count in zip(requirements, counts):
            if count <= 0:
                continue
            tasks.append(
                {
                    "requirement_id": req["id"],
                    "requirement_text": f"【{req['title']}】\n{req.get('description') or ''}",
                    "count": count,
                    "label": req["title"],
                }
            )
        return tasks
    return [
        {
            "requirement_id": None,
            "requirement_text": manual_text,
            "count": total_count,
            "label": "自定义需求",
        }
    ]


def _normalize_text_field(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, list):
        lines: List[str] = []
        for index, item in enumerate(value, start=1):
            text = str(item).strip()
            if not text:
                continue
            if re.match(r"^\d+\.", text):
                lines.append(text)
            else:
                lines.append(f"{index}. {text}")
        return "\n".join(lines) if lines else None
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return text or None


def normalize_testcase_item(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(item)
    for field in ("preconditions", "steps", "expected_results", "tags"):
        if field in normalized:
            normalized[field] = _normalize_text_field(normalized[field])
    title = str(normalized.get("title") or "未命名用例").strip()
    normalized["title"] = title or "未命名用例"
    priority = str(normalized.get("priority") or "P1").strip().upper()
    normalized["priority"] = priority if priority in {"P0", "P1", "P2", "P3"} else "P1"
    return normalized


def _parse_llm_response(content: str) -> List[Dict]:
    content = content.strip()
    if not content:
        raise ValueError("LLM 返回内容为空")

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        array_match = re.search(r"\[[\s\S]*\]", content)
        object_match = re.search(r"\{[\s\S]*\}", content)
        if array_match:
            data = json.loads(array_match.group())
        elif object_match:
            data = json.loads(object_match.group())
        else:
            raise ValueError("LLM 返回内容不是有效 JSON") from None

    if isinstance(data, dict) and "testcases" in data:
        cases = data["testcases"]
    elif isinstance(data, list):
        cases = data
    else:
        raise ValueError("LLM 返回格式不符合预期，需要 JSON 数组或包含 testcases 字段的对象")

    if not isinstance(cases, list):
        raise ValueError("LLM 返回格式不符合预期，testcases 必须是数组")

    return [normalize_testcase_item(case) for case in cases if isinstance(case, dict)]


def _parse_requirements_response(content: str) -> List[Dict]:
    content = content.strip()
    if not content:
        raise ValueError("LLM 返回内容为空")

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\n?", "", content)
        content = re.sub(r"\n?```$", "", content)
        content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        array_match = re.search(r"\[[\s\S]*\]", content)
        object_match = re.search(r"\{[\s\S]*\}", content)
        if array_match:
            data = json.loads(array_match.group())
        elif object_match:
            data = json.loads(object_match.group())
        else:
            raise ValueError("LLM 返回内容不是有效 JSON") from None

    if isinstance(data, dict) and "requirements" in data:
        return data["requirements"]
    if isinstance(data, list):
        return data
    raise ValueError("LLM 返回格式不符合预期，需要 JSON 数组或包含 requirements 字段的对象")


def _mock_requirements(document_text: str) -> List[Dict]:
    lines = [line.strip() for line in document_text.splitlines() if line.strip()]
    candidates = []
    for line in lines:
        if len(line) < 4:
            continue
        title = line[:50]
        if title in {item["title"] for item in candidates}:
            continue
        candidates.append(
            {
                "title": title,
                "description": line,
                "req_type": "functional",
                "priority": "P1" if len(candidates) < 3 else "P2",
            }
        )
        if len(candidates) >= 8:
            break

    if candidates:
        return candidates

    summary = document_text[:80].replace("\n", " ")
    return [
        {
            "title": f"{summary}相关需求",
            "description": document_text[:500],
            "req_type": "functional",
            "priority": "P1",
        }
    ]


def _normalize_requirement_item(item: Dict) -> Dict:
    req_type = item.get("req_type") or "functional"
    if req_type not in {"functional", "api", "performance", "security"}:
        req_type = "functional"
    priority = item.get("priority") or "P1"
    if priority not in {"P0", "P1", "P2", "P3"}:
        priority = "P1"
    title = (item.get("title") or "未命名需求点").strip()[:200]
    description = (item.get("description") or "").strip()
    return {
        "title": title,
        "description": description,
        "req_type": req_type,
        "priority": priority,
    }


def _build_request_payload(
    *,
    model: str,
    api_base: str,
    system_prompt: str,
    user_prompt: str,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": False,
    }

    if "bigmodel.cn" in api_base:
        payload["tools"] = [{"type": "web_search", "web_search": {"enable": False}}]

    return payload


def _extract_llm_error(response: httpx.Response) -> str:
    try:
        body = response.json()
        error = body.get("error", body)
        if isinstance(error, dict):
            return error.get("message") or str(error)
        return str(error)
    except Exception:
        return response.text[:300] or f"HTTP {response.status_code}"


async def call_llm_chat(
    *,
    api_base: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """发一次 OpenAI 兼容 chat/completions 请求，返回非空 content；失败抛 ValueError。"""
    timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)
    payload = _build_request_payload(
        model=model, api_base=api_base, system_prompt=system_prompt, user_prompt=user_prompt
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{api_base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            if response.status_code >= 400:
                raise ValueError(_extract_llm_error(response))
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content") or ""
    except httpx.TimeoutException as exc:
        raise ValueError("LLM 请求超时，请稍后重试或检查网络连接") from exc
    except httpx.HTTPError as exc:
        raise ValueError(f"LLM 网络请求失败: {exc}") from exc
    if not content.strip():
        raise ValueError("LLM 返回内容为空，请检查模型名称或 API 配置")
    return content


async def generate_testcases(
    requirement_text: str,
    case_type: str,
    count: int,
    *,
    api_base: str,
    api_key: str,
    model: str,
    mock_mode: bool,
    existing_titles: Optional[List[str]] = None,
    batch_index: int = 1,
    batch_total: int = 1,
) -> Tuple[List[Dict], str]:
    if mock_mode:
        all_cases = _mock_cases(requirement_text, count, case_type)
        if existing_titles:
            all_cases = [item for item in all_cases if item.get("title") not in existing_titles]
        return all_cases[:count], "mock"
    if not api_key:
        raise ValueError("当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式")

    batch_hint = ""
    if batch_total > 1:
        batch_hint = f"\n这是第 {batch_index}/{batch_total} 批生成，请确保与已有用例不重复。"
    exclude_hint = ""
    if existing_titles:
        titles = "、".join(existing_titles[:30])
        exclude_hint = f"\n已有用例标题（请勿重复）：{titles}"

    user_prompt = f"""需求描述：
{requirement_text}

请生成 {count} 条{_case_type_label(case_type)}测试用例。
要求：title、preconditions、steps、expected_results、tags 全部使用简体中文；步骤请用「1. 2. 3.」编号。
严格按 JSON 对象格式输出：{{"testcases":[...]}}。{batch_hint}{exclude_hint}"""

    timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)
    request_payload = _build_request_payload(
        model=model,
        api_base=api_base,
        system_prompt=SYSTEM_PROMPT,
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

            body = response.json()
            message = body.get("choices", [{}])[0].get("message", {})
            content = message.get("content") or ""
            if not content.strip():
                raise ValueError("LLM 返回内容为空，请检查模型名称或 API 配置")
            return _parse_llm_response(content), "llm"
    except httpx.TimeoutException as exc:
        raise ValueError("LLM 请求超时，请稍后重试或检查网络连接") from exc
    except httpx.HTTPError as exc:
        raise ValueError(f"LLM 网络请求失败: {exc}") from exc


async def stream_generate_batches(
    tasks: List[Dict[str, Any]],
    case_type: str,
    *,
    api_base: str,
    api_key: str,
    model: str,
    mock_mode: bool,
    batch_size: int = 8,
    concurrency: int = 4,
) -> AsyncIterator[Tuple[List[Dict], str, int, int, Optional[int], str, Optional[str]]]:
    existing_titles: List[str] = []
    titles_lock = asyncio.Lock()
    mode = "mock" if mock_mode else "llm"
    batch_plan: List[Dict[str, Any]] = []
    for task in tasks:
        for batch_count in split_generation_batches(task["count"], batch_size):
            batch_plan.append({**task, "batch_count": batch_count})
    total_batches = len(batch_plan) or 1
    worker_count = max(1, min(concurrency, total_batches))
    semaphore = asyncio.Semaphore(worker_count)

    async def run_batch(index: int, plan: Dict[str, Any]):
        async with semaphore:
            async with titles_lock:
                titles_snapshot = list(existing_titles) if existing_titles else None
            try:
                cases_data, current_mode = await generate_testcases(
                    plan["requirement_text"],
                    case_type,
                    plan["batch_count"],
                    api_base=api_base,
                    api_key=api_key,
                    model=model,
                    mock_mode=mock_mode,
                    existing_titles=titles_snapshot,
                    batch_index=index,
                    batch_total=total_batches,
                )
            except ValueError as exc:
                return index, plan, [], mode, str(exc)

            async with titles_lock:
                if cases_data:
                    existing_titles.extend(item.get("title", "") for item in cases_data if item.get("title"))
            return index, plan, cases_data, current_mode, None

    pending = [
        asyncio.create_task(run_batch(index, plan))
        for index, plan in enumerate(batch_plan, start=1)
    ]
    for finished in asyncio.as_completed(pending):
        index, plan, cases_data, batch_mode, task_error = await finished
        if batch_mode:
            mode = batch_mode
        yield (
            cases_data,
            mode,
            index,
            total_batches,
            plan["requirement_id"],
            plan["label"],
            task_error,
        )


async def extract_requirements_from_document(
    document_text: str,
    *,
    api_base: str,
    api_key: str,
    model: str,
    mock_mode: bool,
) -> Tuple[List[Dict], str]:
    items: List[Dict] = []
    async for item, mode, *_rest in stream_extract_requirements(
        document_text,
        api_base=api_base,
        api_key=api_key,
        model=model,
        mock_mode=mock_mode,
    ):
        items.append(item)
    if not items:
        raise ValueError("未能从文档中提取到有效需求点")
    return items, mode if items else ("mock" if mock_mode else "llm")


async def _extract_requirements_from_chunk(
    chunk_text: str,
    *,
    chunk_index: int,
    chunk_total: int,
    api_base: str,
    api_key: str,
    model: str,
    existing_titles: Optional[List[str]] = None,
) -> List[Dict]:
    exclude_hint = ""
    if existing_titles:
        titles = "、".join(existing_titles[:40])
        exclude_hint = f"\n已提取的需求点标题（请勿重复）：{titles}"

    user_prompt = f"""这是需求文档的第 {chunk_index}/{chunk_total} 部分，请仅基于以下内容提取独立需求点。
{exclude_hint}

文档片段：
{chunk_text}

请提取本片段中的独立需求点，严格按 JSON 对象格式输出：{{"requirements":[...]}}。"""

    timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)
    request_payload = _build_request_payload(
        model=model,
        api_base=api_base,
        system_prompt=REQUIREMENT_EXTRACT_PROMPT,
        user_prompt=user_prompt,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=request_payload,
        )
        if response.status_code >= 400:
            raise ValueError(_extract_llm_error(response))

        body = response.json()
        message = body.get("choices", [{}])[0].get("message", {})
        content = message.get("content") or ""
        if not content.strip():
            return []
        return [_normalize_requirement_item(item) for item in _parse_requirements_response(content)]


async def stream_extract_requirements(
    document_text: str,
    *,
    api_base: str,
    api_key: str,
    model: str,
    mock_mode: bool,
) -> AsyncIterator[Tuple[Dict, str, int, int, int]]:
    """Yield requirement item, mode, current count, chunk index, chunk total."""
    if mock_mode:
        items = [_normalize_requirement_item(item) for item in _mock_requirements(document_text)]
        chunk_total = max(len(items), 1)
        for index, item in enumerate(items, start=1):
            await asyncio.sleep(0.12)
            yield item, "mock", index, index, chunk_total
        return

    if not api_key:
        raise ValueError("当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式")

    chunks = split_document_chunks(document_text)
    chunk_total = len(chunks)
    seen_titles = set()
    current = 0
    mode = "llm"

    try:
        for chunk_index, chunk in enumerate(chunks, start=1):
            chunk_items = await _extract_requirements_from_chunk(
                chunk,
                chunk_index=chunk_index,
                chunk_total=chunk_total,
                api_base=api_base,
                api_key=api_key,
                model=model,
                existing_titles=list(seen_titles) or None,
            )
            for item in chunk_items:
                title = item.get("title")
                if not title or title in seen_titles:
                    continue
                seen_titles.add(title)
                current += 1
                yield item, mode, current, chunk_index, chunk_total
                await asyncio.sleep(0)
    except httpx.TimeoutException as exc:
        raise ValueError("LLM 请求超时，请稍后重试或检查网络连接") from exc
    except httpx.HTTPError as exc:
        raise ValueError(f"LLM 网络请求失败: {exc}") from exc

    if current == 0:
        raise ValueError("未能从文档中提取到有效需求点")


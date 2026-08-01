import asyncio
import json
import re
from typing import AsyncIterator, Dict, List, Optional
from urllib.parse import parse_qs

import httpx

from app.services.ai_service import _extract_llm_error
from app.services.assistant_knowledge import (
    build_assistant_system_prompt,
    domain_labels_for_page_context,
    find_guide_answer,
    section_labels_for_page_context,
)

_DOMAIN_LABELS = domain_labels_for_page_context()
_SECTION_LABELS = section_labels_for_page_context()


def _format_page_context(page_path: Optional[str]) -> str:
    if not page_path:
        return ""
    parts: List[str] = [f"用户当前 URL：{page_path}"]
    if page_path.startswith("/hub") and "workspace" not in page_path:
        parts.append("位于 Hub（首页/项目列表/动态等）")
    match = re.search(r"/hub/workspace/(\d+)", page_path)
    if match:
        parts.append(f"位于项目工作区，项目 ID {match.group(1)}")
    if "#" in page_path:
        fragment = page_path.split("#", 1)[1]
        qs = parse_qs(fragment, keep_blank_values=True)
        domain = (qs.get("domain") or [None])[0]
        section = (qs.get("section") or [None])[0]
        biz = (qs.get("biz") or [None])[0]
        if domain:
            parts.append(f"当前域：{_DOMAIN_LABELS.get(domain, domain)}")
        if section:
            parts.append(f"当前功能区：{_SECTION_LABELS.get(section, section)}")
        if biz:
            parts.append(f"自动化子域 biz={biz}")
    return "\n\n" + "\n".join(parts)


def _mock_assistant_reply(question: str, page_path: Optional[str] = None) -> str:
    q = question or ""
    page_hint = _format_page_context(page_path)

    guide = find_guide_answer(q)
    if guide:
        return guide + page_hint

    return (
        "您好！我是 AI 质量平台助手。\n"
        "可问我平台操作（项目、需求、用例、接口自动化等），也可聊其它话题。\n"
        "当前为 **Mock 模式**，复杂问题请在「系统 → 全局设置」配置大模型后重试。"
        + page_hint
    )


async def _stream_mock_text(text: str) -> AsyncIterator[str]:
    chunk_size = 8
    for index in range(0, len(text), chunk_size):
        yield text[index : index + chunk_size]
        await asyncio.sleep(0.02)


def _trim_messages(messages: List[Dict[str, str]], limit: int = 12) -> List[Dict[str, str]]:
    cleaned = []
    for item in messages[-limit:]:
        role = (item.get("role") or "").strip()
        content = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})
    return cleaned


async def stream_assistant_reply(
    messages: List[Dict[str, str]],
    *,
    api_base: str,
    api_key: str,
    model: str,
    mock_mode: bool,
    page_path: Optional[str] = None,
    preset_reply: Optional[str] = None,
) -> AsyncIterator[str]:
    trimmed = _trim_messages(messages)
    if not trimmed or trimmed[-1]["role"] != "user":
        raise ValueError("请提供用户消息")

    user_question = trimmed[-1]["content"]

    if preset_reply is not None:
        async for token in _stream_mock_text(preset_reply):
            yield token
        return

    if mock_mode:
        reply = _mock_assistant_reply(user_question, page_path)
        async for token in _stream_mock_text(reply):
            yield token
        return

    if not api_key:
        raise ValueError("当前未配置 API Key，请前往「系统管理 → 全局设置」配置大模型，或开启 Mock 模式")

    page_context = _format_page_context(page_path)
    system_prompt = build_assistant_system_prompt(user_question)

    llm_messages = [{"role": "system", "content": system_prompt + page_context}]
    llm_messages.extend(trimmed)

    payload = {
        "model": model,
        "messages": llm_messages,
        "temperature": 0.6,
        "max_tokens": 2048,
        "stream": True,
    }
    if "bigmodel.cn" in api_base:
        payload["tools"] = [{"type": "web_search", "web_search": {"enable": False}}]

    timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)
    url = f"{api_base.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    raw = await response.aread()
                    fake = httpx.Response(response.status_code, content=raw, request=response.request)
                    raise ValueError(_extract_llm_error(fake))

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content") or ""
                    if content:
                        yield content
    except httpx.TimeoutException as exc:
        raise ValueError("大模型请求超时，请稍后重试") from exc
    except httpx.HTTPError as exc:
        raise ValueError(f"大模型网络请求失败: {exc}") from exc

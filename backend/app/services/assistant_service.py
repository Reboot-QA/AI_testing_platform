import asyncio
import json
from typing import AsyncIterator, Dict, List, Optional

import httpx

from app.constants.menus import MENU_DEFINITIONS
from app.services.ai_service import _extract_llm_error
_PAGE_HINTS = {item["path"]: item["label"] for item in MENU_DEFINITIONS if item.get("path")}


def _build_platform_guide() -> str:
    lines = ["## 平台功能菜单"]
    groups: Dict[str, List[str]] = {}
    for item in MENU_DEFINITIONS:
        parent = item.get("parent_label")
        label = item["label"]
        path = item.get("path", "")
        entry = f"- {label}（{path}）" if path else f"- {label}"
        key = parent or "主菜单"
        groups.setdefault(key, []).append(entry)

    for group, entries in groups.items():
        lines.append(f"\n### {group}")
        lines.extend(entries)

    lines.append(
        """

## 典型操作流程
1. **项目管理**：侧边栏「项目管理」→ 新建项目 → 填写名称与描述。
2. **需求管理**：「需求文档」上传文档 AI 提取需求点，或在「需求点」手工添加 → 将状态改为「已评审」。
3. **AI 生成用例**：「用例管理 → AI 生成」→ 选择项目、大模型、关联已评审需求 → 生成后写入用例库。
4. **用例执行**：「用例执行」创建执行轮次，记录手工测试结果。
5. **接口自动化**：「环境配置」→「套件与用例」→ 执行或定时任务 →「测试报告」查看结果。
6. **系统管理**：「全局设置」配置 LLM；「用户管理」「部门权限」管理账号与数据共享；「权限管理」分配菜单。

## 回答要求
- 使用简体中文，步骤清晰，可带菜单路径。
- 只回答与本 AI 质量测试平台相关的问题；无关问题礼貌说明。
- 不确定的功能不要编造，可建议用户查看对应菜单或联系管理员。
- 若用户要求你在平台内**自动操作/演示**，说明平台支持浏览器自动化，用户确认后助手会代为点击和填写表单。
"""
    )
    return "\n".join(lines)


ASSISTANT_SYSTEM_PROMPT = f"""你是「AI 质量平台」的智能助手，帮助测试人员使用本系统完成项目管理、需求、用例、接口自动化等工作。

{_build_platform_guide()}
"""


def _mock_assistant_reply(question: str, page_path: Optional[str] = None) -> str:
    q = (question or "").lower()
    page_hint = ""
    if page_path and page_path in _PAGE_HINTS:
        page_hint = f"\n\n您当前在「{_PAGE_HINTS[page_path]}」页面（{page_path}）。"

    if any(k in q for k in ("项目", "新建")):
        return (
            "**创建项目步骤：**\n"
            "1. 左侧菜单进入「项目管理」\n"
            "2. 点击「新建项目」，填写名称与描述\n"
            "3. 保存后可在该项目下添加需求与用例\n\n"
            "同部门用户可共享项目数据；管理员可查看全部部门。"
            + page_hint
        )
    if any(k in q for k in ("ai", "生成", "用例")):
        return (
            "**AI 生成用例步骤：**\n"
            "1. 先在「需求点」将需求评审为「已评审」\n"
            "2. 进入「用例管理 → AI 生成」\n"
            "3. 选择项目、大模型（系统管理 → 全局设置中配置）\n"
            "4. 勾选已评审需求或输入需求描述，设置条数后生成\n"
            "5. 生成结果自动进入「用例库」"
            + page_hint
        )
    if any(k in q for k in ("接口", "自动化", "套件", "定时")):
        return (
            "**接口自动化流程：**\n"
            "1. 「环境配置」：为项目配置 Base URL、变量\n"
            "2. 「套件与用例」：组织目录、编写接口用例\n"
            "3. 可立即执行或配置「定时任务」\n"
            "4. 「测试报告」查看执行结果与详情"
            + page_hint
        )
    if any(k in q for k in ("部门", "用户", "权限", "管理员")):
        return (
            "**系统与权限：**\n"
            "- 「部门权限」：创建部门，同部门共享项目数据\n"
            "- 「用户管理」：创建账号并分配部门\n"
            "- 「权限管理」：为测试员分配可访问的菜单\n"
            "- 管理员默认可访问全部数据与系统菜单"
            + page_hint
        )
    if any(k in q for k in ("需求", "文档", "提取")):
        return (
            "**需求管理：**\n"
            "1. 「需求文档」上传 Word/PDF 等，可用 AI 提取需求点\n"
            "2. 「需求点」列表维护、评审（approved）后可用于 AI 生成用例"
            + page_hint
        )

    return (
        "您好！我是 AI 质量平台助手，可以帮您了解：\n"
        "- 如何创建项目、添加需求\n"
        "- 如何使用 AI 生成测试用例\n"
        "- 接口自动化与环境配置\n"
        "- 部门权限与用户管理\n\n"
        "请直接描述您想完成的操作，我会给出步骤指引。"
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

    page_context = ""
    if page_path and page_path in _PAGE_HINTS:
        page_context = f"\n\n用户当前页面：{_PAGE_HINTS[page_path]}（{page_path}）"

    llm_messages = [{"role": "system", "content": ASSISTANT_SYSTEM_PROMPT + page_context}]
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

import asyncio
import json
import re
from typing import AsyncIterator, Dict, List, Optional
from urllib.parse import parse_qs

import httpx

from app.services.ai_service import _extract_llm_error

# 与前端 Hub 壳 WorkspaceTree / GlobalRail 一致（非旧版侧边栏路径）
_DOMAIN_LABELS = {"requirements": "需求", "functional": "功能", "automation": "自动化"}
_SECTION_LABELS = {
    "req-overview": "需求概览",
    "req-docs": "AI 分析需求",
    "req-points": "需求点",
    "func-overview": "功能测试概览",
    "ai": "AI 生成功能用例",
    "func-cases": "功能用例库",
    "func-runs": "手工执行",
    "overview": "自动化概览",
    "apis": "接口目录",
    "datamodels": "数据模型",
    "cases": "接口用例",
    "scenarios": "场景测试",
    "suites": "测试套件",
    "schedules": "定时任务",
    "reports": "测试报告",
    "trash": "回收站",
}


def _build_platform_guide() -> str:
    return f"""
## 信息架构（必读，勿使用已废弃的旧菜单名）
- **Hub 首页** `/hub`：项目列表（左侧「项目」）、动态、系统管理入口。
- **项目工作区** `/hub/workspace/{{项目ID}}`：左侧全局栏三个域 —— **需求**、**功能**、**自动化**（不是旧版「项目管理 / 用例管理」侧边栏）。
- 域内左侧树展开具体功能；URL hash 形如 `#domain=requirements&section=req-points`。

## 需求域
- **需求概览**
- **需求资产 → AI 分析需求**：上传文档 →「AI 解析需求点」→ 勾选「导入到需求点」
- **需求资产 → 需求点**：工具栏 **「+ 添加需求」**；字段含标题、类型、优先级、描述；状态 **草稿 / 已评审 / 已关闭**。**已评审** 后才可关联 **AI 生成功能用例**。

## 功能域
- **AI 生成功能用例**：选大模型、关联已评审需求 →「开始生成」→ 写入 **功能用例库**
- **功能用例库**：「手动添加」维护用例
- **手工执行**：「新建测试单」→ 选需求点 → 逐条标记通过/失败/阻塞

## 自动化域（接口自动化）
- **接口目录**、**数据模型**、**接口用例**、**场景测试**、**测试套件**、**定时任务**、**测试报告**、**AI 任务中心**、**回收站**
- 运行前在顶部选择 **运行环境**；点 **运行** 后可在 **测试报告** 查看步骤

## 系统管理（Hub 左侧「系统」，需权限）
- **全局设置**（LLM Provider）、**用户管理**、**部门权限**、**权限管理**、日志等

## 典型操作流程
1. Hub **项目** → **新建项目** → 进入项目工作区
2. **需求 → 需求点 → + 添加需求** → 状态改 **已评审**
3. **功能 → AI 生成功能用例** → 关联需求 → **开始生成**
4. **功能 → 手工执行 → 新建测试单** 执行功能用例
5. **自动化 → 接口用例 / 场景测试 / 测试套件 → 运行 → 测试报告**

## 回答要求
- 使用简体中文；涉及本系统时，步骤中的按钮/菜单名必须与上文一致（例如写「+ 添加需求」，不要写「新建需求点」）。
- 不要引用旧路径 `/projects`、`/requirements` 作为当前入口（它们会 redirect 到 Hub）。
- 用户问平台以外的问题时，可正常解答；问平台功能时优先给出准确操作步骤。
- 不确定的平台功能不要编造，可建议用户查看对应菜单或联系管理员。
- **禁止**代替用户在浏览器中点击、跳转或填写表单，即使用户说「帮我操作」也只输出文字步骤。
"""


ASSISTANT_SYSTEM_PROMPT = f"""你是「AI 质量平台」的智能助手，熟悉本平台的项目 / 需求 / 用例 / 接口自动化等操作。

用户也可能提问其它领域问题，请如实、简洁作答。当问题与本平台相关时，优先结合下文信息架构给出可执行步骤。

{_build_platform_guide()}
"""


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

    if any(k in q for k in ("创建项目", "新建项目", "如何创建项目")) or (
        "项目" in q and any(k in q for k in ("创建", "新建", "如何"))
    ):
        return (
            "**创建项目：**\n"
            "1. 打开 Hub（/hub），左侧点 **项目**\n"
            "2. 点 **新建项目**，填写项目名与描述\n"
            "3. 进入该项目 **工作区**，使用需求/功能/自动化三域"
            + page_hint
        )
    if any(k in q for k in ("创建需求", "添加需求", "如何创建需求", "需求点")):
        return (
            "**创建需求（需求点）：**\n"
            "1. 进入 **项目工作区** → 左侧 **需求**\n"
            "2. 打开 **需求点** → 点 **+ 添加需求**\n"
            "3. 填写标题、类型、优先级、描述并保存\n"
            "4. 将状态改为 **已评审** 后可被 AI 生成功能用例关联\n"
            "（可选：在 **AI 分析需求** 上传文档并导入到需求点）"
            + page_hint
        )
    if any(k in q for k in ("生成用例", "如何生成", "AI 生成")):
        return (
            "**生成用例：**\n"
            "1. **功能 → AI 生成功能用例**：选大模型与 **已评审** 需求 → **开始生成**\n"
            "2. 或 **功能 → 功能用例库 → 手动添加**\n"
            "3. 接口侧：**自动化 → 接口用例** 中添加或 AI 生成"
            + page_hint
        )
    if any(k in q for k in ("执行用例", "如何执行", "手工执行", "测试单")):
        return (
            "**执行用例：**\n"
            "1. **功能 → 手工执行 → 新建测试单**，选择需求点\n"
            "2. 进入测试单标记每条用例结果\n"
            "3. 自动化：**场景测试/测试套件** 选环境后 **运行**，在 **测试报告** 查看"
            + page_hint
        )
    if "报告" in q:
        return (
            "**查看测试报告：**\n"
            "1. 进入 **项目工作区** → 左侧 **自动化**\n"
            "2. 在左侧树打开 **测试报告**\n"
            "3. 在列表中点击某条记录或 **查看**，右侧抽屉可看步骤明细、通过率，并支持导出"
            + page_hint
        )
    if any(k in q for k in ("接口自动化", "如何使用接口", "场景测试", "测试套件")):
        return (
            "**接口自动化：**\n"
            "项目工作区 → **自动化**：接口目录 → 接口用例 → 场景测试 → 测试套件；"
            "定时任务与测试报告在同一左侧树；运行前选顶部环境。"
            + page_hint
        )
    if any(k in q for k in ("部门", "用户", "权限", "管理员", "全局设置")):
        return (
            "**系统与权限：**\n"
            "Hub 左侧 **系统**：全局设置（大模型）、用户管理、部门权限、权限管理。"
            + page_hint
        )
    if any(k in q for k in ("需求", "文档", "提取", "解析")):
        return (
            "**需求：**\n"
            "**AI 分析需求** 上传文档 → **AI 解析需求点** → 导入；"
            "或在 **需求点** 用 **+ 添加需求** 手工维护。"
            + page_hint
        )

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

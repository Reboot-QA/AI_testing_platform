import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.services.ai_service import _extract_llm_error

# 前端 data-assistant 标识与说明
ACTION_CATALOG = """
可用浏览器自动化步骤（按顺序放入 actions 数组）：
1. navigate - 跳转页面: {"type":"navigate","path":"/projects"}
2. wait - 等待毫秒: {"type":"wait","ms":500}
3. click - 点击元素: {"type":"click","target":"projects.create_btn"}
4. fill - 填写输入: {"type":"fill","target":"projects.form.name","value":"项目名称"}

已注册 target：
- menu.projects（侧边栏项目管理）
- projects.create_btn（新建项目按钮）
- projects.form.name（项目名称输入框）
- projects.form.description（项目描述输入框）
- projects.form.submit（确定提交）
- menu.dashboard / menu.requirements / menu.ai_generate / menu.testcases 等菜单路径见平台菜单
"""

ACTION_SYSTEM_PROMPT = f"""你是 AI 质量平台的「操作规划器」。用户可能要求你在平台内自动演示或执行操作。
你必须只输出一个 JSON 对象，不要 markdown，不要其它文字。

格式：
{{
  "reply": "给用户的简短说明（简体中文）",
  "actions": [ ...步骤数组... ],
  "needs_confirmation": true
}}

规则：
- 用户要求「演示」「帮我操作」「自动创建」「直接创建」等时，必须生成可执行的 actions，needs_confirmation 为 true。
- 仅咨询「怎么做」「如何操作」且未要求代操作时，actions 为空数组。
- 创建项目典型步骤：navigate /projects → wait → click projects.create_btn → fill name/description → click submit。
- 项目名称从用户话术中提取；未指定时用「AI演示项目」。
- 不要生成未注册的 target。
{ACTION_CATALOG}
"""


def _extract_project_name(text: str) -> str:
    patterns = [
        r"[「\"']([^「\"']+)[」\"']",
        r"(?:叫做|名为|名称是|名字叫|叫)\s*[：:]?\s*([^\s，。；;！!？?\n]{2,30})",
        r"项目(?:名称)?[：:]\s*([^\s，。；;！!？?\n]{2,30})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).strip()
            if name and name not in {"项目", "一个项目", "新项目"}:
                return name[:50]
    return "AI演示项目"


def _wants_automation(text: str) -> bool:
    q = text or ""
    automation_keywords = ("演示", "帮我", "帮忙", "自动", "直接", "操作一下", "执行", "创建一", "新建一", "建一")
    return any(keyword in q for keyword in automation_keywords)


def _mock_plan_actions(
    question: str,
    page_path: Optional[str] = None,
    messages: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    q = question or ""
    context = " ".join(
        item.get("content", "")
        for item in (messages or [])[-4:]
        if item.get("role") in {"user", "assistant"}
    )
    combined = f"{context} {q}"

    if _wants_automation(q) and any(k in combined for k in ("项目", "新建", "创建")):
        name = _extract_project_name(combined)
        desc = "由 AI 助手自动创建的演示项目"
        if "描述" in q:
            desc_match = re.search(r"描述[为是：:]\s*([^\n]{2,100})", q)
            if desc_match:
                desc = desc_match.group(1).strip()
        return {
            "reply": f"好的，我将为您在浏览器中演示创建项目「{name}」，请确认后自动执行以下步骤。",
            "actions": [
                {"type": "navigate", "path": "/projects", "label": "打开项目管理"},
                {"type": "wait", "ms": 600},
                {"type": "click", "target": "projects.create_btn", "label": "点击新建项目"},
                {"type": "wait", "ms": 400},
                {"type": "fill", "target": "projects.form.name", "value": name, "label": f"填写项目名称：{name}"},
                {"type": "fill", "target": "projects.form.description", "value": desc, "label": "填写项目描述"},
                {"type": "click", "target": "projects.form.submit", "label": "提交创建"},
            ],
            "needs_confirmation": True,
        }

    if _wants_automation(q) and any(k in q for k in ("跳转", "打开", "进入", "去")):
        path = page_path or "/dashboard"
        if "项目" in q:
            path = "/projects"
        elif "需求" in q:
            path = "/requirements"
        elif "用例" in q and "生成" in q:
            path = "/ai-generate"
        elif "用例" in q:
            path = "/testcases"
        return {
            "reply": f"好的，我将为您跳转到对应页面（{path}）。",
            "actions": [
                {"type": "navigate", "path": path, "label": f"跳转到 {path}"},
            ],
            "needs_confirmation": True,
        }

    return {"reply": "", "actions": [], "needs_confirmation": False}


async def plan_assistant_actions(
    messages: List[Dict[str, str]],
    *,
    api_base: str,
    api_key: str,
    model: str,
    mock_mode: bool,
    page_path: Optional[str] = None,
) -> Dict[str, Any]:
    if not messages or messages[-1].get("role") != "user":
        return {"reply": "", "actions": [], "needs_confirmation": False}

    question = messages[-1]["content"]
    if not _wants_automation(question):
        return {"reply": "", "actions": [], "needs_confirmation": False}

    if mock_mode:
        return _mock_plan_actions(question, page_path, messages)

    if not api_key:
        return _mock_plan_actions(question, page_path)

    page_hint = f"\n当前页面：{page_path}" if page_path else ""
    llm_messages = [
        {"role": "system", "content": ACTION_SYSTEM_PROMPT + page_hint},
        {"role": "user", "content": question},
    ]
    payload = {
        "model": model,
        "messages": llm_messages,
        "temperature": 0.2,
        "max_tokens": 1200,
        "stream": False,
    }
    if "bigmodel.cn" in api_base:
        payload["tools"] = [{"type": "web_search", "web_search": {"enable": False}}]

    timeout = httpx.Timeout(connect=15.0, read=60.0, write=15.0, pool=15.0)
    url = f"{api_base.rstrip('/')}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            if response.status_code >= 400:
                raise ValueError(_extract_llm_error(response))
            body = response.json()
            content = body.get("choices", [{}])[0].get("message", {}).get("content") or ""
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content).strip()
            plan = json.loads(content)
            if not isinstance(plan, dict):
                raise ValueError("规划结果格式错误")
            plan.setdefault("reply", "")
            plan.setdefault("actions", [])
            plan.setdefault("needs_confirmation", bool(plan.get("actions")))
            return plan
    except (json.JSONDecodeError, ValueError, httpx.HTTPError):
        return _mock_plan_actions(question, page_path, messages)

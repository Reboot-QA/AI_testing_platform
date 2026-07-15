import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.services.ai_service import _extract_llm_error

DEFAULT_WAIT_MS = 1000


def _wait_step(label: str = "等待页面就绪", ms: int = DEFAULT_WAIT_MS) -> Dict[str, Any]:
    return {"type": "wait", "ms": ms, "label": label}

# 前端 data-assistant 标识与说明
ACTION_CATALOG = """
可用浏览器自动化步骤（按顺序放入 actions 数组）：
1. navigate - 跳转页面: {"type":"navigate","path":"/projects"}
2. wait - 等待毫秒: {"type":"wait","ms":1000,"label":"等待页面就绪"}
3. click - 点击元素: {"type":"click","target":"projects.create_btn"}
4. fill - 填写输入: {"type":"fill","target":"projects.form.name","value":"项目名称"}
5. invoke - 调用页面内处理器: {"type":"invoke","handler":"aiGenerate.startGenerate","label":"开始生成"}

已注册 target：
- menu.projects（侧边栏项目管理）
- projects.create_btn（新建项目按钮）
- projects.form.name（项目名称输入框）
- projects.form.description（项目描述输入框）
- projects.form.submit（确定提交）

已注册 invoke handler（由对应页面挂载后可用）：
- requirements.ensureProject / requirements.createDemo（需求管理）
- aiGenerate.prepareDemo / aiGenerate.startGenerate（AI 生成用例）
- testcases.ensureProject（用例库）
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
- 接口自动化相关请求一律引导到新版工作台 /apifox（老 /api-automation 已下线）。
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
    automation_keywords = (
        "演示",
        "帮我",
        "帮忙",
        "自动",
        "直接",
        "操作一下",
        "执行",
        "创建一",
        "新建一",
        "建一",
        "导入",
    )
    return any(keyword in q for keyword in automation_keywords)


def _project_create_actions(name: str, desc: str) -> List[Dict[str, Any]]:
    return [
        {"type": "navigate", "path": "/projects", "label": "打开项目管理"},
        _wait_step("等待页面加载"),
        {"type": "click", "target": "projects.create_btn", "label": "点击新建项目"},
        _wait_step("等待弹窗打开"),
        {"type": "fill", "target": "projects.form.name", "value": name, "label": f"填写项目名称：{name}"},
        {"type": "fill", "target": "projects.form.description", "value": desc, "label": "填写项目描述"},
        {"type": "click", "target": "projects.form.submit", "label": "提交创建"},
    ]


def _get_demo_preset_plan(preset: str) -> Optional[Dict[str, Any]]:
    if preset in {"create_project", "project_management_full"}:
        name = "AI演示项目"
        desc = "项目管理全流程演示项目"
        return {
            "reply": "好的，我将为您演示项目管理全流程：创建项目并完成基本配置，请稍候观看。",
            "actions": _project_create_actions(name, desc),
            "needs_confirmation": False,
        }

    if preset == "testcase_management_full":
        return {
            "reply": "好的，我将为您演示用例管理全流程：AI 生成用例并进入用例库查看，请稍候观看。",
            "actions": [
                {"type": "navigate", "path": "/ai-generate", "label": "打开 AI生成用例"},
                _wait_step("等待 AI 生成页加载"),
                {"type": "invoke", "handler": "aiGenerate.prepareDemo", "label": "准备生成配置"},
                _wait_step("等待表单填充完成"),
                {"type": "invoke", "handler": "aiGenerate.startGenerate", "label": "AI 生成用例"},
                _wait_step("等待生成完成", ms=1500),
                {"type": "navigate", "path": "/testcases", "label": "进入用例库"},
                _wait_step("等待用例库加载", ms=1500),
                {"type": "invoke", "handler": "testcases.ensureProject", "label": "查看项目用例列表"},
            ],
            "needs_confirmation": False,
        }

    if preset == "requirement_management_full":
        return {
            "reply": "好的，我将为您演示需求管理全流程：创建演示需求，请稍候观看。",
            "actions": [
                {"type": "navigate", "path": "/requirements", "label": "打开需求管理"},
                _wait_step("等待页面加载"),
                {"type": "invoke", "handler": "requirements.ensureProject", "label": "选择项目"},
                _wait_step("等待项目切换完成"),
                {"type": "invoke", "handler": "requirements.createDemo", "label": "创建演示需求"},
            ],
            "needs_confirmation": False,
        }

    if preset in {"ai_generate"}:
        return {
            "reply": "好的，我将为您打开 AI生成用例、填充演示需求并点击「开始生成」，请稍候观看。",
            "actions": [
                {"type": "navigate", "path": "/ai-generate", "label": "打开 AI生成用例"},
                _wait_step("等待 AI 生成页加载"),
                {"type": "invoke", "handler": "aiGenerate.prepareDemo", "label": "选择项目并填充演示需求"},
                _wait_step("等待表单填充完成"),
                {"type": "invoke", "handler": "aiGenerate.startGenerate", "label": "点击开始生成"},
            ],
            "needs_confirmation": False,
        }

    if preset in {"api_automation", "api_automation_management_full"}:
        # 老接口自动化模块已软下线（G2a）：改为引导到新版 apifox 工作台，不再调用已下线的组件 handler
        return {
            "reply": "接口自动化已升级为新版工作台，我这就为您打开。",
            "actions": [
                {"type": "navigate", "path": "/apifox", "label": "打开接口自动化工作台"},
            ],
            "needs_confirmation": False,
        }

    if preset == "create_project_and_test":
        name = "AI演示项目"
        desc = "由 AI 助手演示创建，并进入 AI 生成用例"
        actions = _project_create_actions(name, desc)
        actions.extend(
            [
                _wait_step("等待项目创建完成"),
                {"type": "navigate", "path": "/ai-generate", "label": "进入 AI生成用例"},
                _wait_step("等待 AI 生成页加载"),
                {"type": "invoke", "handler": "aiGenerate.prepareDemo", "label": "准备生成配置"},
                _wait_step("等待表单填充完成"),
                {"type": "invoke", "handler": "aiGenerate.startGenerate", "label": "点击开始生成"},
            ]
        )
        return {
            "reply": "好的，我将演示创建项目、进入 AI生成用例并点击「开始生成」，请稍候观看。",
            "actions": actions,
            "needs_confirmation": False,
        }

    return None


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

    if _wants_automation(q) and any(k in combined for k in ("项目", "新建", "创建")) and "套件" not in combined:
        name = _extract_project_name(combined)
        desc = "由 AI 助手自动创建的演示项目"
        if "描述" in q:
            desc_match = re.search(r"描述[为是：:]\s*([^\n]{2,100})", q)
            if desc_match:
                desc = desc_match.group(1).strip()
        return {
            "reply": f"好的，我将为您在浏览器中演示创建项目「{name}」，请确认后自动执行以下步骤。",
            "actions": _project_create_actions(name, desc),
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
    demo_preset: Optional[str] = None,
) -> Dict[str, Any]:
    if not messages or messages[-1].get("role") != "user":
        return {"reply": "", "actions": [], "needs_confirmation": False}

    if demo_preset:
        preset_plan = _get_demo_preset_plan(demo_preset)
        if preset_plan:
            return preset_plan

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

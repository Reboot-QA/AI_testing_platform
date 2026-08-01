import json
import re
from typing import Any, Dict, List, Optional

import httpx

from app.services.ai_service import _extract_llm_error

DEFAULT_WAIT_MS = 1000


def _wait_step(label: str = "等待页面就绪", ms: int = DEFAULT_WAIT_MS) -> Dict[str, Any]:
    return {"type": "wait", "ms": ms, "label": label}

# 新版信息架构（v2 壳）：首页 /hub（项目列表 + 跨项目动态）；业务功能都在项目工作区
# 工作区深链使用 /hub/workspace/{pid}/<子路径>；旧 hash 仅由前端守卫兼容。
# 各功能 → (domain, section, biz)；biz 仅自动化域需要。
_NAV_MAP: Dict[str, str] = {
    "req-points": "requirements/points",
    "req-docs": "requirements/documents",
    "func-cases": "functional/cases",
    "ai-generate": "functional/ai-generate",
    "manual-run": "functional/runs",
    "apis": "automation/apis",
    "cases": "automation/cases",
    "scenarios": "automation/scenarios",
    "suites": "automation/suites",
    "schedules": "automation/schedules",
    "reports": "automation/reports",
    "trash": "automation/trash",
    "automation": "automation",
}


def _pid_from_path(page_path: Optional[str]) -> Optional[str]:
    """从当前页 route.path 解析项目 id（新壳工作区 /hub/workspace/:pid，不含 hash）。"""
    if not page_path:
        return None
    match = re.search(r"/hub/workspace/(\d+)", page_path)
    return match.group(1) if match else None


def _ws_path(pid: str, key: str) -> str:
    """按功能 key 拼项目工作区具名子路径。"""
    return f"/hub/workspace/{pid}/{_NAV_MAP[key]}"


def _nav_key(text: str) -> Optional[str]:
    """从用户话术判定要去的功能区（新版 IA）。"""
    q = text or ""
    if "回收站" in q:
        return "trash"
    if "报告" in q:
        return "reports"
    if "定时" in q:
        return "schedules"
    if "场景" in q:
        return "scenarios"
    if "套件" in q:
        return "suites"
    if "需求" in q:
        return "req-docs" if ("文档" in q or "分析" in q) else "req-points"
    if "用例" in q and "生成" in q:
        return "ai-generate"
    if "接口" in q and "用例" in q:
        return "cases"
    if "用例" in q:
        return "func-cases"
    if "手工" in q or "执行" in q:
        return "manual-run"
    if "接口" in q or "自动化" in q:
        return "automation"
    return None


# 前端 data-assistant 锚点 / invoke handler（随 v2 壳逐页重挂后的当前清单）
ACTION_CATALOG = """
可用浏览器自动化步骤（按顺序放入 actions 数组）：
1. navigate - 跳转页面: {"type":"navigate","path":"/hub#view=projects"} 或项目工作区深链 {"type":"navigate","path":"/hub/workspace/12/functional/cases"}
2. wait - 等待毫秒: {"type":"wait","ms":1000,"label":"等待页面就绪"}
3. click - 点击元素: {"type":"click","target":"projects.create_btn"}
4. fill - 填写输入: {"type":"fill","target":"projects.form.name","value":"项目名称"}
5. invoke - 调用页面内处理器: {"type":"invoke","handler":"aiGenerate.startGenerate","label":"开始生成"}

已注册 click/fill target（须先 navigate 到对应页面，元素才存在）：
- 首页 /hub：projects.create_btn / projects.form.name / projects.form.description / projects.form.submit
- 需求点（domain=requirements&section=req-points）：requirements.create_btn / requirements.form.title / requirements.form.description / requirements.form.submit

已注册 invoke handler（导航到对应 section 挂载后可用）：
- 项目列表：projects.prepareDemo / projects.submitDemo
- AI 生成用例（section=ai）：aiGenerate.prepareDemo / aiGenerate.startGenerate
- 需求点：requirements.ensureProject / requirements.createDemo
- 功能用例库（section=func-cases）：testcases.ensureProject
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
- 平台首页是 /hub；「项目管理」固定使用 /hub#view=projects。
- 各业务功能都在**项目工作区**内，深链格式 /hub/workspace/{{项目id}}/<子路径>：
  · 需求点 requirements/points；需求文档分析 requirements/documents
  · 功能用例库 functional/cases；AI 生成用例 functional/ai-generate；手工执行 functional/runs
  · 接口自动化：automation/apis、automation/cases、automation/scenarios、automation/suites、automation/schedules、automation/reports、automation/trash
- 项目工作区功能需要「项目id」：若当前上下文没有项目，停止动作并提示用户先选择项目。
- 旧路径 /projects /apifox /api-automation /testcases /requirements /ai-generate /dashboard 已废弃，一律改用上面的 /hub 深链。
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
        {"type": "navigate", "path": "/hub#view=projects", "label": "打开项目列表"},
        _wait_step("等待页面加载"),
        {
            "type": "invoke",
            "handler": "projects.prepareDemo",
            "payload": {"name": name, "description": desc},
            "label": f"填写项目信息：{name}",
        },
        _wait_step("展示项目配置", ms=800),
        {
            "type": "invoke",
            "handler": "projects.submitDemo",
            "payload": {"next_route": "WorkspaceSettingsBasic"},
            "label": "创建项目并进入基础设置",
        },
    ]


def _project_required_plan() -> Dict[str, Any]:
    return {
        "reply": "该演示需要项目上下文。请先在 AI 助手中选择一个项目，再重新开始演示。",
        "actions": [],
        "needs_confirmation": False,
    }


def _get_demo_preset_plan(
    preset: str,
    page_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    pid = _pid_from_path(page_path)

    if preset in {"create_project", "project_management_full"}:
        name = "AI演示项目"
        desc = "项目管理全流程演示项目"
        return {
            "reply": "好的，我将为您演示项目管理全流程：创建项目并完成基本配置，请稍候观看。",
            "actions": _project_create_actions(name, desc),
            "needs_confirmation": False,
        }

    if preset in {
        "testcase_management_full",
        "requirement_management_full",
        "ai_generate",
        "api_automation",
        "api_automation_management_full",
    } and not pid:
        return _project_required_plan()

    if preset == "testcase_management_full":
        return {
            "reply": "好的，我将为您演示用例管理全流程：AI 生成用例并进入用例库查看，请稍候观看。",
            "actions": [
                {"type": "navigate", "path": _ws_path(pid, "ai-generate"), "label": "打开 AI生成用例"},
                _wait_step("等待 AI 生成页加载"),
                {"type": "invoke", "handler": "aiGenerate.prepareDemo", "label": "准备生成配置"},
                _wait_step("等待表单填充完成"),
                {"type": "invoke", "handler": "aiGenerate.startGenerate", "label": "AI 生成用例"},
                _wait_step("等待生成完成", ms=1500),
                {"type": "navigate", "path": _ws_path(pid, "func-cases"), "label": "进入用例库"},
                _wait_step("等待用例库加载", ms=1500),
                {"type": "invoke", "handler": "testcases.ensureProject", "label": "查看项目用例列表"},
            ],
            "needs_confirmation": False,
        }

    if preset == "requirement_management_full":
        return {
            "reply": "好的，我将为您演示需求管理全流程：创建演示需求，请稍候观看。",
            "actions": [
                {"type": "navigate", "path": _ws_path(pid, "req-points"), "label": "打开需求管理"},
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
                {"type": "navigate", "path": _ws_path(pid, "ai-generate"), "label": "打开 AI生成用例"},
                _wait_step("等待 AI 生成页加载"),
                {"type": "invoke", "handler": "aiGenerate.prepareDemo", "label": "选择项目并填充演示需求"},
                _wait_step("等待表单填充完成"),
                {"type": "invoke", "handler": "aiGenerate.startGenerate", "label": "点击开始生成"},
            ],
            "needs_confirmation": False,
        }

    if preset in {"api_automation", "api_automation_management_full"}:
        return {
            "reply": "好的，我将按新版工作台层级演示接口目录、场景、套件、定时任务与测试报告。",
            "actions": [
                {"type": "navigate", "path": _ws_path(pid, "apis"), "label": "查看接口目录"},
                _wait_step("展示接口目录", ms=900),
                {"type": "navigate", "path": _ws_path(pid, "scenarios"), "label": "查看场景编排"},
                _wait_step("展示场景编排", ms=900),
                {"type": "navigate", "path": _ws_path(pid, "suites"), "label": "查看测试套件"},
                _wait_step("展示测试套件", ms=900),
                {"type": "navigate", "path": _ws_path(pid, "schedules"), "label": "查看定时任务"},
                _wait_step("展示定时任务", ms=900),
                {"type": "navigate", "path": _ws_path(pid, "reports"), "label": "查看测试报告"},
            ],
            "needs_confirmation": False,
        }

    if preset == "create_project_and_test":
        return {
            "reply": "请先完成项目创建，再从 AI 助手中选择该项目运行用例管理演示。",
            "actions": _project_create_actions("AI演示项目", "由 AI 助手演示创建"),
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
        pid = _pid_from_path(page_path)
        # 「项目管理/项目列表」在首页
        if "项目" in q and not any(k in q for k in ("接口", "用例", "需求", "场景", "套件")):
            return {
                "reply": "好的，我将为您跳转到项目列表。",
                "actions": [{"type": "navigate", "path": "/hub#view=projects", "label": "跳转到项目列表"}],
                "needs_confirmation": True,
            }
        key = _nav_key(q)
        if key and pid:
            path = _ws_path(pid, key)
            return {
                "reply": f"好的，我将为您跳转到对应模块（{path}）。",
                "actions": [{"type": "navigate", "path": path, "label": f"跳转到 {path}"}],
                "needs_confirmation": True,
            }
        if key and not pid:
            return {
                "reply": "这个功能在具体项目的工作区里。请先在 AI 助手中选择项目，再重新执行。",
                "actions": [],
                "needs_confirmation": False,
            }
        path = page_path or "/hub"
        return {
            "reply": f"好的，我将为您跳转到对应页面（{path}）。",
            "actions": [{"type": "navigate", "path": path, "label": f"跳转到 {path}"}],
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
        preset_plan = _get_demo_preset_plan(demo_preset, page_path)
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

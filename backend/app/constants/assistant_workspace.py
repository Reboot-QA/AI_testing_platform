"""Hub 工作区导航树（与 frontend WorkspaceTree / GlobalRail 对齐，供 AI 助手知识库使用）。"""

from typing import Dict, List, Optional, TypedDict


class WorkspaceLeaf(TypedDict):
    key: str
    label: str
    section: str
    biz: Optional[str]


class WorkspaceGroup(TypedDict, total=False):
    title: str
    items: List[WorkspaceLeaf]


DOMAIN_LABELS: Dict[str, str] = {
    "requirements": "需求",
    "functional": "功能",
    "automation": "自动化",
    "ai_tasks": "AI 任务",
    "settings": "设置",
}

SECTION_LABELS: Dict[str, str] = {
    "req-overview": "需求概览",
    "req-docs": "AI 分析需求",
    "req-points": "需求点",
    "func-overview": "功能测试概览",
    "ai": "AI 生成功能用例",
    "func-cases": "功能用例库",
    "func-runs": "手工执行",
    "func-reports": "功能测试报告",
    "overview": "自动化概览",
    "apis": "接口目录",
    "datamodels": "数据模型",
    "cases": "接口用例",
    "scenarios": "测试场景",
    "suites": "测试套件",
    "schedules": "定时任务",
    "reports": "测试报告",
    "trash": "回收站",
    "ai-overview": "AI 任务概述",
    "ai-req": "AI 需求任务",
    "ai-case": "AI 用例任务",
    "ai-api": "AI 接口任务",
}

HUB_HOME_NAV = [
    {"key": "home", "label": "首页", "path": "/hub#view=home"},
    {"key": "projects", "label": "项目", "path": "/hub#view=projects"},
    {"key": "activity", "label": "动态", "path": "/hub#view=activity"},
    {"key": "system", "label": "系统", "path": "/hub/system"},
]

WORKSPACE_DOMAINS: Dict[str, List[WorkspaceGroup]] = {
    "requirements": [
        {"items": [{"key": "req-overview", "label": "需求概览", "section": "req-overview", "biz": None}]},
        {
            "title": "需求资产",
            "items": [
                {"key": "req-docs", "label": "AI 分析需求", "section": "req-docs", "biz": None},
                {"key": "req-points", "label": "需求点", "section": "req-points", "biz": None},
            ],
        },
    ],
    "functional": [
        {"items": [{"key": "func-overview", "label": "功能测试概览", "section": "func-overview", "biz": None}]},
        {
            "title": "功能用例资产",
            "items": [
                {"key": "func-ai", "label": "AI 生成功能用例", "section": "ai", "biz": None},
                {"key": "func-cases", "label": "功能用例库", "section": "func-cases", "biz": None},
                {"key": "func-runs", "label": "手工执行", "section": "func-runs", "biz": None},
            ],
        },
        {
            "title": "测试报告",
            "items": [
                {"key": "func-reports", "label": "功能测试报告", "section": "func-reports", "biz": None},
            ],
        },
    ],
    "automation": [
        {"items": [{"key": "overview", "label": "自动化概览", "section": "overview", "biz": "autotest"}]},
        {
            "title": "接口管理",
            "items": [
                {"key": "apis", "label": "接口目录", "section": "apis", "biz": "apis"},
                {"key": "datamodels", "label": "数据模型", "section": "datamodels", "biz": "autotest"},
            ],
        },
        {
            "title": "自动化测试",
            "items": [
                {"key": "cases", "label": "接口用例", "section": "cases", "biz": "autotest"},
                {"key": "scenarios", "label": "测试场景", "section": "scenarios", "biz": "autotest"},
                {"key": "suites", "label": "测试套件", "section": "suites", "biz": "autotest"},
                {"key": "schedules", "label": "定时任务", "section": "schedules", "biz": "autotest"},
            ],
        },
        {
            "title": "报告",
            "items": [
                {"key": "reports", "label": "测试报告", "section": "reports", "biz": "reports"},
            ],
        },
        {"items": [{"key": "trash", "label": "回收站", "section": "trash", "biz": "autotest"}]},
    ],
    "ai_tasks": [
        {"items": [{"key": "ai-overview", "label": "AI 任务概述", "section": "ai-overview", "biz": None}]},
        {
            "title": "任务执行",
            "items": [
                {"key": "ai-req", "label": "AI 需求任务", "section": "ai-req", "biz": None},
                {"key": "ai-case", "label": "AI 用例任务", "section": "ai-case", "biz": None},
                {"key": "ai-api", "label": "AI 接口任务", "section": "ai-api", "biz": None},
            ],
        },
    ],
}

# 从业务代码提炼的操作要点（助手专用，非完整规格）
FEATURE_NOTES: List[str] = [
    "需求点状态：草稿 / 已评审 / 已关闭；仅 **已评审** 可关联 AI 生成功能用例。",
    "需求点 **+ 添加需求** 为手工创建；**AI 分析需求** 可上传文档解析后导入需求点。",
    "需求导入：**追加** 忽略 Excel 序号、自动续编；**覆盖** 仅删除无关联用例的需求，已关联用例的需求点保留。",
    "功能用例：AI 生成写入功能用例库；手工执行通过 **新建测试单** 关联需求点执行。",
    "接口自动化：运行前在顶部选择 **运行环境**；接口用例 / 测试场景 / 测试套件均可 **运行**，结果在 **测试报告** 查看。",
    "Hub 右侧栏为 **动态**（失败聚焦、最近报告、定时、手工、AI 任务等聚合）。",
]

ANSWER_RULES: List[str] = [
    "使用简体中文；按钮/菜单名必须与下文导航树一致（如「+ 添加需求」「测试场景」）。",
    "不要引用旧路径 `/projects`、`/requirements` 作为当前入口（会 redirect 到 Hub）。",
    "用户问平台以外的问题时可正常解答；问平台功能时优先给出可执行步骤。",
    "不确定的平台功能不要编造，可建议用户查看对应菜单或联系管理员。",
    "**禁止**代替用户在浏览器中点击、跳转或填写表单，即使用户说「帮我操作」也只输出文字步骤。",
]

from typing import Dict, List

# 菜单权限 key 与 Hub / 项目工作区功能对齐（key 保持稳定，勿随意改名以免破坏已存授权）
MENU_DEFINITIONS: List[Dict[str, str]] = [
    {
        "key": "dashboard",
        "label": "首页",
        "path": "/hub",
        "group": "business",
        "parent": "hub",
        "parent_label": "Hub",
        "hint": "Hub 落地页；取消授权后仍可通过「项目」等入口登录",
    },
    {
        "key": "projects",
        "label": "项目",
        "path": "/hub",
        "group": "business",
        "parent": "hub",
        "parent_label": "Hub",
        "hint": "项目列表、新建项目、进入项目工作区",
    },
    {
        "key": "requirement_docs",
        "label": "AI 分析需求",
        "path": "/hub/workspace",
        "group": "business",
        "parent": "requirements",
        "parent_label": "需求",
        "hint": "上传文档、AI 解析需求点、导入需求点",
    },
    {
        "key": "requirements",
        "label": "需求点",
        "path": "/hub/workspace",
        "group": "business",
        "parent": "requirements",
        "parent_label": "需求",
        "hint": "手工维护需求点、导入导出、关联用例",
    },
    {
        "key": "ai_generate",
        "label": "AI 生成功能用例",
        "path": "/hub/workspace",
        "group": "business",
        "parent": "functional",
        "parent_label": "功能",
        "hint": "基于已评审需求 AI 生成功能用例",
    },
    {
        "key": "testcases",
        "label": "功能用例库",
        "path": "/hub/workspace",
        "group": "business",
        "parent": "functional",
        "parent_label": "功能",
        "hint": "维护功能用例、关联需求点",
    },
    {
        "key": "test_execution",
        "label": "手工执行",
        "path": "/hub/workspace",
        "group": "business",
        "parent": "functional",
        "parent_label": "功能",
        "hint": "新建测试单、标记执行结果、功能测试报告",
    },
    {
        "key": "apifox_workbench",
        "label": "接口自动化",
        "path": "/hub/workspace",
        "group": "business",
        "parent": "automation",
        "parent_label": "自动化",
        "hint": "接口目录、数据模型、接口用例、测试场景、测试套件、定时任务、测试报告、回收站",
    },
    {"key": "system_settings", "label": "全局设置", "path": "/system/settings", "group": "system"},
    {"key": "system_users", "label": "用户管理", "path": "/system/users", "group": "system"},
    {"key": "system_departments", "label": "部门权限", "path": "/system/departments", "group": "system"},
    {"key": "system_permissions", "label": "权限管理", "path": "/system/permissions", "group": "system"},
]

# 项目工作区「AI 任务」域不单独设权限，由下列能力组合决定：
# - AI 需求任务 → requirement_docs
# - AI 用例任务 → ai_generate
# - AI 接口任务 → apifox_workbench

DEFAULT_TESTER_MENUS = [
    "dashboard",
    "projects",
    "apifox_workbench",
    "requirement_docs",
    "requirements",
    "testcases",
    "ai_generate",
    "test_execution",
]

ALL_MENU_KEYS = [item["key"] for item in MENU_DEFINITIONS]

MENU_KEY_SET = set(ALL_MENU_KEYS)

WORKSPACE_PERMISSION_GROUP_KEYS = ("requirements", "functional", "automation")

HUB_PERMISSION_GROUP_KEY = "hub"

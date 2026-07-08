from typing import Dict, List

MENU_DEFINITIONS: List[Dict[str, str]] = [
    {"key": "dashboard", "label": "仪表盘", "path": "/dashboard", "group": "business"},
    {"key": "projects", "label": "项目管理", "path": "/projects", "group": "business"},
    {
        "key": "requirement_docs",
        "label": "AI分析需求",
        "path": "/requirement-docs",
        "group": "business",
        "parent": "requirement_mgmt",
        "parent_label": "需求管理",
    },
    {
        "key": "requirements",
        "label": "需求点",
        "path": "/requirements",
        "group": "business",
        "parent": "requirement_mgmt",
        "parent_label": "需求管理",
    },
    {
        "key": "ai_generate",
        "label": "AI生成用例",
        "path": "/ai-generate",
        "group": "business",
        "parent": "testcase_mgmt",
        "parent_label": "用例管理",
    },
    {
        "key": "testcases",
        "label": "用例库",
        "path": "/testcases",
        "group": "business",
        "parent": "testcase_mgmt",
        "parent_label": "用例管理",
    },
    {
        "key": "test_execution",
        "label": "用例执行",
        "path": "/test-execution",
        "group": "business",
        "parent": "testcase_mgmt",
        "parent_label": "用例管理",
    },
    {
        "key": "api_automation_env",
        "label": "环境配置",
        "path": "/api-automation/env",
        "group": "business",
        "parent": "api_automation_mgmt",
        "parent_label": "接口自动化",
    },
    {
        "key": "api_automation_suites",
        "label": "套件与用例",
        "path": "/api-automation/suites",
        "group": "business",
        "parent": "api_automation_mgmt",
        "parent_label": "接口自动化",
    },
    {
        "key": "api_automation_reports",
        "label": "测试报告",
        "path": "/api-automation/reports",
        "group": "business",
        "parent": "api_automation_mgmt",
        "parent_label": "接口自动化",
    },
    {
        "key": "api_automation_schedule",
        "label": "定时任务",
        "path": "/api-automation/schedule",
        "group": "business",
        "parent": "api_automation_mgmt",
        "parent_label": "接口自动化",
    },
    {"key": "system_settings", "label": "全局设置", "path": "/system/settings", "group": "system"},
    {"key": "system_users", "label": "用户管理", "path": "/system/users", "group": "system"},
    {"key": "system_departments", "label": "部门权限", "path": "/system/departments", "group": "system"},
    {"key": "system_permissions", "label": "权限管理", "path": "/system/permissions", "group": "system"},
    {"key": "system_logs", "label": "日志监控", "path": "/system/logs", "group": "system"},
]

DEFAULT_TESTER_MENUS = [
    "dashboard",
    "projects",
    "requirement_docs",
    "requirements",
    "testcases",
    "ai_generate",
    "test_execution",
    "api_automation_env",
    "api_automation_suites",
    "api_automation_reports",
    "api_automation_schedule",
]

ALL_MENU_KEYS = [item["key"] for item in MENU_DEFINITIONS]

MENU_KEY_SET = set(ALL_MENU_KEYS)

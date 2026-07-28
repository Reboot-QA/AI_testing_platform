"""AI 助手操作规划器 · 新版 IA 导航路径映射（v2 壳：功能改为项目内 hash 深链）。

被测：app/services/assistant_action_service.py 的路径推导（纯函数 + mock 规划分支）。
"""

import pytest

from app.services import assistant_action_service as svc


@pytest.mark.parametrize(
    "page_path,expected",
    [
        ("/hub/workspace/12", "12"),
        ("/hub/workspace/7#domain=functional&section=ai", "7"),
        ("/hub", None),
        (None, None),
        ("/system/settings", None),
    ],
)
def test_pid_from_path(page_path, expected):
    assert svc._pid_from_path(page_path) == expected


@pytest.mark.parametrize(
    "key,expected",
    [
        ("func-cases", "/hub/workspace/5#domain=functional&section=func-cases"),
        ("ai-generate", "/hub/workspace/5#domain=functional&section=ai"),
        ("scenarios", "/hub/workspace/5#domain=automation&biz=autotest&section=scenarios"),
        ("reports", "/hub/workspace/5#domain=automation&biz=reports&section=reports"),
        ("req-points", "/hub/workspace/5#domain=requirements&section=req-points"),
    ],
)
def test_ws_path_matches_hash_serialization(key, expected):
    assert svc._ws_path("5", key) == expected


def test_nav_jump_in_project_builds_deep_link():
    plan = svc._mock_plan_actions("帮我打开场景测试", page_path="/hub/workspace/9")

    assert plan["actions"][0]["type"] == "navigate"
    assert plan["actions"][0]["path"] == "/hub/workspace/9#domain=automation&biz=autotest&section=scenarios"


def test_nav_jump_without_project_stops_before_invalid_actions():
    plan = svc._mock_plan_actions("帮我打开用例库", page_path="/hub")

    assert plan["actions"] == []
    assert "项目" in plan["reply"]


def test_nav_project_management_goes_to_project_view():
    plan = svc._mock_plan_actions("帮我打开项目管理", page_path="/hub/workspace/9")

    assert plan["actions"][0]["path"] == "/hub#view=projects"


def test_preset_uses_project_scoped_paths_when_pid_present():
    plan = svc._get_demo_preset_plan("api_automation_management_full", page_path="/hub/workspace/3")

    navs = [a["path"] for a in plan["actions"] if a["type"] == "navigate"]
    assert navs == [
        "/hub/workspace/3#domain=automation&biz=apis&section=apis",
        "/hub/workspace/3#domain=automation&biz=autotest&section=scenarios",
        "/hub/workspace/3#domain=automation&biz=autotest&section=suites",
        "/hub/workspace/3#domain=automation&biz=autotest&section=schedules",
        "/hub/workspace/3#domain=automation&biz=reports&section=reports",
    ]


def test_preset_without_pid_stops_before_unmounted_handlers():
    plan = svc._get_demo_preset_plan("testcase_management_full", page_path=None)

    assert plan["actions"] == []
    assert "项目" in plan["reply"]


def test_project_preset_uses_project_view_and_semantic_handlers():
    plan = svc._get_demo_preset_plan("project_management_full", page_path="/hub")

    assert plan["actions"][0]["path"] == "/hub#view=projects"
    handlers = [a["handler"] for a in plan["actions"] if a["type"] == "invoke"]
    assert handlers == ["projects.prepareDemo", "projects.submitDemo"]


def test_explicit_project_context_path_drives_requirement_preset():
    plan = svc._get_demo_preset_plan("requirement_management_full", page_path="/hub/workspace/18")

    navs = [a["path"] for a in plan["actions"] if a["type"] == "navigate"]
    assert navs == ["/hub/workspace/18#domain=requirements&section=req-points"]


def test_no_stale_global_routes_in_prompt():
    for dead in ("/api-automation", "/testcases", "/ai-generate", "/requirements", "/dashboard"):
        assert f'"{dead}"' not in svc.ACTION_SYSTEM_PROMPT

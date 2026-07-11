"""S1 场景步骤树 · 读写/校验/存量兼容。

被测：app/services/apifox/scenario_service.py 的树落库(_write_steps)与回显(_out)。
"""

import pytest

from app.routers.apifox.scenario_schemas import ScenarioCreate, ScenarioUpdate, StepIn
from app.services.apifox import scenario_service as svc


def _case_step(case_id: int, name: str = "") -> StepIn:
    return StepIn(type="case", ref_case_id=case_id, name=name or None)


def _group(name: str, children: list) -> StepIn:
    return StepIn(type="group", name=name, children=children)


def test_roundtrip_group_wrapping_cases_preserves_tree(db, make_case):
    case_a = make_case(name="A")
    case_b = make_case(name="B")
    case_c = make_case(name="C")

    out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="登录链路",
            steps=[
                _group("准备", [_case_step(case_a.id), _case_step(case_b.id)]),
                _case_step(case_c.id),
            ],
        ),
    )

    assert [s.type for s in out.steps] == ["group", "case"]
    group = out.steps[0]
    assert group.name == "准备"
    assert [c.ref_case_id for c in group.children] == [case_a.id, case_b.id]
    assert out.steps[1].ref_case_id == case_c.id


def test_roundtrip_two_level_nested_groups(db, make_case):
    inner_case = make_case(name="inner")

    out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="嵌套",
            steps=[_group("外", [_group("内", [_case_step(inner_case.id)])])],
        ),
    )

    outer = out.steps[0]
    inner = outer.children[0]
    assert inner.type == "group"
    assert inner.children[0].ref_case_id == inner_case.id


def test_empty_group_is_saved(db):
    out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(name="空组", steps=[_group("空", [])])
    )

    assert out.steps[0].type == "group"
    assert out.steps[0].children == []


def test_leaf_step_with_children_is_rejected(db, make_case):
    case = make_case()
    bad = StepIn(type="case", ref_case_id=case.id, children=[_case_step(case.id)])

    with pytest.raises(ValueError, match="容器"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="非法", steps=[bad]))


def test_invalid_step_type_is_rejected(db):
    bad = StepIn(type="branch", name="x")

    with pytest.raises(ValueError, match="无效的步骤类型"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="非法", steps=[bad]))


def test_nesting_beyond_max_depth_is_rejected(db, make_case):
    case = make_case()
    node: StepIn = _case_step(case.id)
    for _ in range(svc._MAX_NEST_DEPTH + 2):
        node = _group("g", [node])

    with pytest.raises(ValueError, match="嵌套层级过深"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="过深", steps=[node]))


def test_legacy_flat_steps_roundtrip_unchanged(db, make_case):
    """存量扁平场景（无 group、parent 为空）读写行为不变——回归护栏。"""
    case = make_case(name="旧用例")

    out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="旧场景",
            steps=[_case_step(case.id), StepIn(type="wait", wait_ms=500)],
        ),
    )

    assert [s.type for s in out.steps] == ["case", "wait"]
    assert all(s.children == [] for s in out.steps)
    assert out.steps[1].wait_ms == 500


def test_update_replaces_tree(db, make_case):
    case = make_case(name="A")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(name="s", steps=[_case_step(case.id)])
    )
    scenario = svc.repo.get_scenario(db, scenario_out.id)

    updated = svc.update_scenario(
        db, scenario, ScenarioUpdate(steps=[_group("新组", [_case_step(case.id)])])
    )

    assert [s.type for s in updated.steps] == ["group"]
    assert updated.steps[0].children[0].ref_case_id == case.id

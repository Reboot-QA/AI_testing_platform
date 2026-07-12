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


_COND = {"left": "{{x}}", "operator": "eq", "right": "1"}


def _if(then_children: list, else_children: list | None = None, condition: dict = _COND) -> StepIn:
    children = list(then_children)
    if else_children is not None:
        children.append(StepIn(type="else", children=else_children))
    return StepIn(type="if", config={"condition": condition}, children=children)


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


def test_if_roundtrip_with_then_and_else(db, make_case):
    then_c = make_case(name="THEN")
    else_c = make_case(name="ELSE")

    out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="条件",
            steps=[_if([_case_step(then_c.id)], else_children=[_case_step(else_c.id)])],
        ),
    )

    if_step = out.steps[0]
    assert if_step.type == "if"
    assert if_step.config["condition"]["operator"] == "eq"
    then_children = [c for c in if_step.children if c.type != "else"]
    else_step = next(c for c in if_step.children if c.type == "else")
    assert then_children[0].ref_case_id == then_c.id
    assert else_step.children[0].ref_case_id == else_c.id


def test_if_roundtrip_without_else(db, make_case):
    then_c = make_case(name="THEN")

    out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(name="s", steps=[_if([_case_step(then_c.id)])])
    )

    if_step = out.steps[0]
    assert if_step.type == "if"
    assert all(c.type != "else" for c in if_step.children)


def test_if_missing_condition_is_rejected(db, make_case):
    bad = StepIn(type="if", children=[_case_step(make_case().id)])

    with pytest.raises(ValueError, match="condition"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_if_invalid_operator_is_rejected(db, make_case):
    bad = _if([_case_step(make_case().id)], condition={"left": "a", "operator": "xx", "right": "b"})

    with pytest.raises(ValueError, match="操作符"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_else_outside_if_is_rejected(db, make_case):
    bad = StepIn(type="else", children=[_case_step(make_case().id)])

    with pytest.raises(ValueError, match="else"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_two_else_under_if_is_rejected(db, make_case):
    a, b = make_case(name="a"), make_case(name="b")
    bad = StepIn(
        type="if",
        config={"condition": _COND},
        children=[StepIn(type="else", children=[_case_step(a.id)]),
                  StepIn(type="else", children=[_case_step(b.id)])],
    )

    with pytest.raises(ValueError, match="至多一个 else"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_nested_if_in_else_roundtrip(db, make_case):
    inner = make_case(name="inner")
    outer_then = make_case(name="outer_then")

    out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="elif",
            steps=[_if([_case_step(outer_then.id)], else_children=[_if([_case_step(inner.id)])])],
        ),
    )

    else_step = next(c for c in out.steps[0].children if c.type == "else")
    nested_if = else_step.children[0]
    assert nested_if.type == "if"
    assert nested_if.children[0].ref_case_id == inner.id


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


# ---------- S3 循环 loop：校验 + 往返 ----------
def _loop(config: dict, children: list) -> StepIn:
    return StepIn(type="loop", config=config, children=children)


def test_loop_count_roundtrip(db, make_case):
    body = make_case(name="body")
    out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s", steps=[_loop({"mode": "count", "count": 3}, [_case_step(body.id)])]
        ),
    )

    loop = out.steps[0]
    assert loop.type == "loop"
    assert loop.config == {"mode": "count", "count": 3}
    assert loop.children[0].ref_case_id == body.id


def test_loop_list_roundtrip(db, make_case):
    body = make_case(name="body")
    cfg = {"mode": "list", "list_var": "items", "item_var": "it", "index_var": "i"}
    out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(name="s", steps=[_loop(cfg, [_case_step(body.id)])])
    )

    assert out.steps[0].config == cfg


def test_loop_while_roundtrip(db, make_case):
    body = make_case(name="body")
    cfg = {"mode": "while", "condition": {"left": "{{x}}", "operator": "lt", "right": "3"},
           "max_iterations": 10}
    out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(name="s", steps=[_loop(cfg, [_case_step(body.id)])])
    )

    assert out.steps[0].config["max_iterations"] == 10


def test_loop_count_zero_is_rejected(db, make_case):
    bad = _loop({"mode": "count", "count": 0}, [_case_step(make_case().id)])

    with pytest.raises(ValueError, match="循环次数"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_loop_list_missing_var_is_rejected(db, make_case):
    bad = _loop({"mode": "list"}, [_case_step(make_case().id)])

    with pytest.raises(ValueError, match="list_var"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_loop_while_invalid_condition_is_rejected(db, make_case):
    bad = _loop({"mode": "while", "max_iterations": 5}, [_case_step(make_case().id)])

    with pytest.raises(ValueError, match="condition"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_loop_while_nonpositive_maxiter_is_rejected(db, make_case):
    bad = _loop(
        {"mode": "while", "condition": {"left": "1", "operator": "eq", "right": "1"}, "max_iterations": 0},
        [_case_step(make_case().id)],
    )

    with pytest.raises(ValueError, match="max_iterations"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_loop_invalid_mode_is_rejected(db, make_case):
    bad = _loop({"mode": "forever"}, [_case_step(make_case().id)])

    with pytest.raises(ValueError, match="循环模式"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))


def test_loop_nested_in_loop_roundtrip(db, make_case):
    inner = make_case(name="inner")
    out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_loop({"mode": "count", "count": 2},
                         [_loop({"mode": "count", "count": 3}, [_case_step(inner.id)])])],
        ),
    )

    outer = out.steps[0]
    nested = outer.children[0]
    assert nested.type == "loop" and nested.config["count"] == 3
    assert nested.children[0].ref_case_id == inner.id


def test_loop_while_maxiter_over_limit_is_rejected(db, make_case):
    bad = _loop(
        {"mode": "while", "condition": {"left": "1", "operator": "eq", "right": "1"},
         "max_iterations": 999999},
        [_case_step(make_case().id)],
    )

    with pytest.raises(ValueError, match="max_iterations"):
        svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=[bad]))

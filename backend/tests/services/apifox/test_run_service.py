"""S1 场景树执行 · 分组顺序展开/深度/禁用组/计数一致。

被测：app/services/apifox/run_service.py 的 _run_scenario_block / _count_scenario_steps。
用例执行(engine.execute_case)打桩，避免真实 HTTP——只验证遍历编排与落库。
"""

import pytest

from app.models.apifox.run import ApifoxRunStep
from app.routers.apifox.scenario_schemas import ScenarioCreate, StepIn
from app.services.apifox import run_engine, run_service
from app.services.apifox import scenario_service as svc


@pytest.fixture
def stub_execute_case(monkeypatch):
    """execute_case 桩：回 passed + 最小 detail，不发网络请求。"""

    def _fake(db, case, endpoint, environment, variables, assertions, extracts):
        return "passed", {
            "method": endpoint.method,
            "url": endpoint.path,
            "extracted": {},
            "scoped": [],
        }

    monkeypatch.setattr(run_engine, "execute_case", _fake)


def _case_step(case_id):
    return StepIn(type="case", ref_case_id=case_id)


def _group(name, children, enabled=True):
    return StepIn(type="group", name=name, children=children, enabled=enabled)


def _if(condition, then_children, else_children=None):
    children = list(then_children)
    if else_children is not None:
        children.append(StepIn(type="else", children=else_children))
    return StepIn(type="if", config={"condition": condition}, children=children)


_TRUE = {"left": "1", "operator": "eq", "right": "1"}
_FALSE = {"left": "1", "operator": "eq", "right": "2"}


def _run(db, scenario_out):
    scenario = svc.repo.get_scenario(db, scenario_out.id)
    events = list(
        run_service.iter_scenario_run(
            db, scenario, environment=None, triggered_by="test", user_id=1
        )
    )
    steps = (
        db.query(ApifoxRunStep)
        .filter(ApifoxRunStep.run_id == events[0]["run_id"])
        .order_by(ApifoxRunStep.id)
        .all()
    )
    return events, steps


def test_group_children_execute_in_order_with_depth(db, make_case, stub_execute_case):
    a, b, c = make_case(name="A"), make_case(name="B"), make_case(name="C")
    scenario_out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="s",
            steps=[_group("组", [_case_step(a.id), _case_step(b.id)]), _case_step(c.id)],
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.case_name for s in steps] == ["A", "B", "C"]
    assert [s.depth for s in steps] == [1, 1, 0]


def test_disabled_group_skips_its_children(db, make_case, stub_execute_case):
    inside = make_case(name="组内")
    top = make_case(name="顶层")
    scenario_out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="s",
            steps=[_group("禁用组", [_case_step(inside.id)], enabled=False), _case_step(top.id)],
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.case_name for s in steps] == ["顶层"]


def test_count_matches_executed_steps(db, make_case, stub_execute_case):
    a, b, c = make_case(name="A"), make_case(name="B"), make_case(name="C")
    scenario_out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="s",
            steps=[
                _group("外", [_group("内", [_case_step(a.id)]), _case_step(b.id)]),
                _case_step(c.id),
            ],
        ),
    )
    scenario = svc.repo.get_scenario(db, scenario_out.id)

    count = run_service._count_scenario_steps(db, scenario.id)
    _events, steps = _run(db, scenario_out)

    assert count == len(steps) == 3


def test_nested_group_depth_increments(db, make_case, stub_execute_case):
    deep = make_case(name="深")
    scenario_out = svc.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="s", steps=[_group("外", [_group("内", [_case_step(deep.id)])])]
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.depth for s in steps] == [2]


def test_if_true_runs_then_skips_else(db, make_case, stub_execute_case):
    then_c, else_c = make_case(name="THEN"), make_case(name="ELSE")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s", steps=[_if(_TRUE, [_case_step(then_c.id)], else_children=[_case_step(else_c.id)])]
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.case_name for s in steps] == ["THEN"]


def test_if_false_runs_else_skips_then(db, make_case, stub_execute_case):
    then_c, else_c = make_case(name="THEN"), make_case(name="ELSE")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s", steps=[_if(_FALSE, [_case_step(then_c.id)], else_children=[_case_step(else_c.id)])]
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.case_name for s in steps] == ["ELSE"]


def test_if_false_without_else_runs_nothing(db, make_case, stub_execute_case):
    then_c = make_case(name="THEN")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(name="s", steps=[_if(_FALSE, [_case_step(then_c.id)])]),
    )

    _events, steps = _run(db, scenario_out)

    assert steps == []


def test_elif_via_nested_if(db, make_case, stub_execute_case):
    outer_then, inner_then = make_case(name="OUTER"), make_case(name="INNER")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_if(_FALSE, [_case_step(outer_then.id)],
                       else_children=[_if(_TRUE, [_case_step(inner_then.id)])])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.case_name for s in steps] == ["INNER"]


def test_branch_steps_depth_is_if_depth_plus_one(db, make_case, stub_execute_case):
    then_c = make_case(name="THEN")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(name="s", steps=[_if(_TRUE, [_case_step(then_c.id)])]),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.depth for s in steps] == [1]


def test_runtime_extraction_drives_branch(db, make_case, monkeypatch):
    setter, then_c = make_case(name="setter"), make_case(name="THEN")

    def _fake(db_, case, endpoint, environment, variables, assertions, extracts):
        extracted = {"flag": "go"} if case.name == "setter" else {}
        return "passed", {"method": endpoint.method, "url": endpoint.path,
                          "extracted": extracted, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_case_step(setter.id),
                   _if({"left": "{{flag}}", "operator": "eq", "right": "go"}, [_case_step(then_c.id)])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.case_name for s in steps] == ["setter", "THEN"]


# ---------- S3 循环 loop：执行 ----------
def _loop(config, children):
    return StepIn(type="loop", config=config, children=children)


def test_count_loop_runs_body_n_times(db, make_case, stub_execute_case):
    body = make_case(name="B")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s", steps=[_loop({"mode": "count", "count": 3}, [_case_step(body.id)])]
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.case_name for s in steps] == ["B", "B", "B"]
    assert [s.depth for s in steps] == [1, 1, 1]


def test_list_loop_injects_item_each_round(db, make_case, monkeypatch):
    setup, body = make_case(name="setup"), make_case(name="body")
    seen = []

    def _fake(db_, case, endpoint, environment, variables, assertions, extracts):
        extracted = {"items": '["x", "y"]'} if case.name == "setup" else {}
        if case.name == "body":
            seen.append(variables.get("it"))
        return "passed", {"method": endpoint.method, "url": endpoint.path,
                          "extracted": extracted, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_case_step(setup.id),
                   _loop({"mode": "list", "list_var": "items", "item_var": "it"}, [_case_step(body.id)])],
        ),
    )

    _events, _steps = _run(db, scenario_out)

    assert seen == ["x", "y"]


def test_while_false_runs_zero_times(db, make_case, stub_execute_case):
    body = make_case(name="B")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s", steps=[_loop(
                {"mode": "while", "condition": {"left": "1", "operator": "eq", "right": "2"},
                 "max_iterations": 5}, [_case_step(body.id)])]
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert steps == []


def test_while_always_true_capped_at_max_iterations(db, make_case, stub_execute_case):
    body = make_case(name="B")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s", steps=[_loop(
                {"mode": "while", "condition": {"left": "1", "operator": "eq", "right": "1"},
                 "max_iterations": 4}, [_case_step(body.id)])]
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert len(steps) == 4


def test_while_counter_flips_stops_at_threshold(db, make_case, monkeypatch):
    init, inc = make_case(name="init"), make_case(name="inc")

    def _fake(db_, case, endpoint, environment, variables, assertions, extracts):
        if case.name == "init":
            extracted = {"i": "0"}
        else:
            extracted = {"i": str(int(variables.get("i", "0")) + 1)}
        return "passed", {"method": endpoint.method, "url": endpoint.path,
                          "extracted": extracted, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_case_step(init.id),
                   _loop({"mode": "while", "condition": {"left": "{{i}}", "operator": "lt", "right": "3"},
                          "max_iterations": 100}, [_case_step(inc.id)])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.case_name for s in steps] == ["init", "inc", "inc", "inc"]


def test_nested_loop_multiplies_iterations(db, make_case, stub_execute_case):
    inner = make_case(name="I")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_loop({"mode": "count", "count": 2},
                         [_loop({"mode": "count", "count": 3}, [_case_step(inner.id)])])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert len(steps) == 6
    assert all(s.depth == 2 for s in steps)


def test_nested_loop_index_var_is_scoped_not_leaked(db, make_case, monkeypatch):
    """内层循环用完 index 后须恢复外层的 index，外层循环体后续步骤不能看到内层残留值。"""
    inner_body, recorder = make_case(name="inner"), make_case(name="rec")
    seen = []

    def _fake(db_, case, endpoint, environment, variables, assertions, extracts):
        if case.name == "rec":
            seen.append(variables.get("index"))
        return "passed", {"method": endpoint.method, "url": endpoint.path,
                          "extracted": {}, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_loop({"mode": "count", "count": 2}, [
                _loop({"mode": "count", "count": 3}, [_case_step(inner_body.id)]),
                _case_step(recorder.id),
            ])],
        ),
    )

    _events, _steps = _run(db, scenario_out)

    assert seen == ["0", "1"]


# ---------- break / continue 流程控制 ----------
def _break():
    return StepIn(type="break")


def _continue():
    return StepIn(type="continue")


def test_break_in_count_loop_stops_after_first_iteration(db, make_case, stub_execute_case):
    body = make_case(name="B")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_loop({"mode": "count", "count": 3}, [_case_step(body.id), _break()])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.step_type for s in steps] == ["case", "break"]


def test_continue_skips_rest_of_body_but_runs_all_rounds(db, make_case, stub_execute_case):
    a, b = make_case(name="A"), make_case(name="B")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_loop({"mode": "count", "count": 2},
                         [_case_step(a.id), _continue(), _case_step(b.id)])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    # 每轮跑 A 后 continue，B 从不执行；跑满 2 轮
    assert [s.case_name for s in steps] == ["A", "跳过本轮", "A", "跳过本轮"]


def test_break_inside_if_triggers_only_on_matching_round(db, make_case, monkeypatch):
    body = make_case(name="body")

    def _fake(db_, case, endpoint, environment, variables, assertions, extracts):
        cur = int(variables.get("i", "0"))
        return "passed", {"method": endpoint.method, "url": endpoint.path,
                          "extracted": {"i": str(cur + 1)}, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_loop({"mode": "count", "count": 5}, [
                _case_step(body.id),
                _if({"left": "{{i}}", "operator": "eq", "right": "3"}, [_break()]),
            ])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    # i 每轮 +1，第 3 轮 body 后 i=3，if 命中 break；body 只跑 3 次
    assert len([s for s in steps if s.step_type == "case"]) == 3
    assert any(s.step_type == "break" for s in steps)


def test_nested_loop_inner_break_only_exits_inner(db, make_case, stub_execute_case):
    inner, outer_mark = make_case(name="I"), make_case(name="O")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_loop({"mode": "count", "count": 2}, [
                _loop({"mode": "count", "count": 3}, [_case_step(inner.id), _break()]),
                _case_step(outer_mark.id),
            ])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    # 内层每轮遇 break 只跑 I 一次即止；外层照常 2 轮，每轮内层 I + 外层 O
    assert [s.case_name for s in steps if s.step_type == "case"] == ["I", "O", "I", "O"]


def test_break_in_while_loop_stops(db, make_case, stub_execute_case):
    body = make_case(name="B")
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[_loop(
                {"mode": "while", "condition": {"left": "1", "operator": "eq", "right": "1"},
                 "max_iterations": 5}, [_case_step(body.id), _break()])],
        ),
    )

    _events, steps = _run(db, scenario_out)

    assert [s.step_type for s in steps] == ["case", "break"]


def test_loop_var_restored_after_break(db, make_case, monkeypatch):
    """break 走异常路径终止循环，S3 的 try/finally 仍须恢复循环变量，不泄漏到循环后。"""
    body, after = make_case(name="body"), make_case(name="after")
    seen = []

    def _fake(db_, case, endpoint, environment, variables, assertions, extracts):
        if case.name == "after":
            seen.append(variables.get("index"))
        return "passed", {"method": endpoint.method, "url": endpoint.path,
                          "extracted": {}, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)
    scenario_out = svc.create_scenario(
        db, project_id=1, data=ScenarioCreate(
            name="s",
            steps=[
                _loop({"mode": "count", "count": 3}, [_case_step(body.id), _break()]),
                _case_step(after.id),
            ],
        ),
    )

    _events, _steps = _run(db, scenario_out)

    assert seen == [None]

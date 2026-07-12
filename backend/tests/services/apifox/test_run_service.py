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

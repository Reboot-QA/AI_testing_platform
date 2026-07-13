"""测试套件执行 · 父运行+子运行 / item 级聚合 / 每项独立 runtime / 失败隔离。

被测：app/services/apifox/run_service.py 的 iter_suite_run。
execute_case 打桩，避免真实 HTTP——只验证套件编排与父/子运行落库。
"""

import pytest

from app.models.apifox.run import ApifoxRun
from app.routers.apifox.scenario_schemas import ScenarioCreate, StepIn
from app.routers.apifox.suite_schemas import SuiteCreate, SuiteItemIn
from app.services.apifox import run_engine, run_service, scenario_service, suite_service


@pytest.fixture
def stub_execute_case(monkeypatch):
    def _fake(db, case, endpoint, environment, variables, assertions, extracts):
        return "passed", {"method": endpoint.method, "url": endpoint.path,
                          "extracted": {}, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)


def _case_item(case_id, enabled=True):
    return SuiteItemIn(target_type="case", target_id=case_id, enabled=enabled)


def _scenario_item(scenario_id):
    return SuiteItemIn(target_type="scenario", target_id=scenario_id)


def _make_scenario_with_case(db, case_id, name="scn"):
    return scenario_service.create_scenario(
        db, project_id=1,
        data=ScenarioCreate(name=name, steps=[StepIn(type="case", ref_case_id=case_id)]),
    )


def _run_suite(db, suite_out):
    suite = suite_service.repo.get_suite(db, suite_out.id)
    events = list(run_service.iter_suite_run(db, suite, environment=None, triggered_by="test", user_id=1))
    parent_id = events[0]["run_id"]
    parent = db.query(ApifoxRun).filter(ApifoxRun.id == parent_id).first()
    children = (
        db.query(ApifoxRun).filter(ApifoxRun.parent_run_id == parent_id).order_by(ApifoxRun.id).all()
    )
    return events, parent, children


def test_suite_run_executes_items_in_order(db, make_case, stub_execute_case):
    a, b = make_case(name="A"), make_case(name="B")
    out = suite_service.create_suite(
        db, project_id=1, data=SuiteCreate(name="s", items=[_case_item(a.id), _case_item(b.id)])
    )

    _events, parent, children = _run_suite(db, out)

    assert parent.target_type == "suite"
    assert [c.target_name for c in children] == ["A", "B"]


def test_suite_run_parent_stats_item_level(db, make_case, monkeypatch):
    ok, bad = make_case(name="OK"), make_case(name="BAD")

    def _fake(db_, case, endpoint, environment, variables, assertions, extracts):
        status = "failed" if case.name == "BAD" else "passed"
        return status, {"method": endpoint.method, "url": endpoint.path, "extracted": {}, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)
    out = suite_service.create_suite(
        db, project_id=1, data=SuiteCreate(name="s", items=[_case_item(ok.id), _case_item(bad.id)])
    )

    _events, parent, _children = _run_suite(db, out)

    assert parent.status == "failed"
    assert (parent.passed_count, parent.failed_count) == (1, 1)
    assert parent.pass_rate == 50.0


def test_suite_child_runs_have_parent_run_id(db, make_case, stub_execute_case):
    a = make_case(name="A")
    out = suite_service.create_suite(db, project_id=1, data=SuiteCreate(name="s", items=[_case_item(a.id)]))

    _events, parent, children = _run_suite(db, out)

    assert all(c.parent_run_id == parent.id for c in children)


def test_suite_items_use_independent_runtime(db, make_case, monkeypatch):
    """核心差异化：前项 extract 的运行时变量不得流入后项（每项独立 fresh runtime）。"""
    setter, reader = make_case(name="setter"), make_case(name="reader")
    seen = []

    def _fake(db_, case, endpoint, environment, variables, assertions, extracts):
        extracted = {"tok": "abc"} if case.name == "setter" else {}
        if case.name == "reader":
            seen.append(variables.get("tok"))
        return "passed", {"method": endpoint.method, "url": endpoint.path,
                          "extracted": extracted, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)
    out = suite_service.create_suite(
        db, project_id=1, data=SuiteCreate(name="s", items=[_case_item(setter.id), _case_item(reader.id)])
    )

    _run_suite(db, out)

    assert seen == [None]


def test_suite_run_disabled_item_skipped(db, make_case, stub_execute_case):
    a, b = make_case(name="A"), make_case(name="B")
    out = suite_service.create_suite(
        db, project_id=1, data=SuiteCreate(name="s", items=[_case_item(a.id, enabled=False), _case_item(b.id)])
    )

    _events, parent, children = _run_suite(db, out)

    assert [c.target_name for c in children] == ["B"]
    assert parent.total_count == 1


def test_suite_run_deleted_target_isolated_as_failed(db, make_case, stub_execute_case):
    gone, alive = make_case(name="GONE"), make_case(name="ALIVE")
    out = suite_service.create_suite(
        db, project_id=1, data=SuiteCreate(name="s", items=[_case_item(gone.id), _case_item(alive.id)])
    )
    from app.repositories.apifox import case_repo
    case_repo.delete(db, gone)
    db.commit()

    events, parent, children = _run_suite(db, out)

    # 缺失目标该项判失败但不阻断；后续项照常执行并生成子运行
    assert parent.failed_count == 1
    assert parent.passed_count == 1
    assert [c.target_name for c in children] == ["ALIVE"]
    item_done = [e for e in events if e["type"] == "item_done"]
    assert item_done[0]["status"] == "failed"


def test_suite_run_empty_yields_passed(db, stub_execute_case):
    out = suite_service.create_suite(db, project_id=1, data=SuiteCreate(name="空套件", items=[]))

    events, parent, children = _run_suite(db, out)

    assert children == []
    assert parent.status == "passed"
    assert parent.total_count == 0
    assert events[-1]["type"] == "suite_done"


def test_suite_run_event_contract(db, make_case, stub_execute_case):
    a = make_case(name="A")
    out = suite_service.create_suite(db, project_id=1, data=SuiteCreate(name="s", items=[_case_item(a.id)]))

    events, _parent, _children = _run_suite(db, out)

    types = [e["type"] for e in events]
    assert types[0] == "suite_start"
    assert "item_start" in types
    assert "item_done" in types
    assert types[-1] == "suite_done"


def test_scenario_run_parent_run_id_none_backward_compat(db, make_case, stub_execute_case):
    """回归：套件外单跑场景，parent_run_id 必须仍为 None（不误标为子运行）。"""
    a = make_case(name="A")
    scn_out = _make_scenario_with_case(db, a.id)
    scenario = scenario_service.repo.get_scenario(db, scn_out.id)

    events = list(
        run_service.iter_scenario_run(db, scenario, environment=None, triggered_by="test", user_id=1)
    )
    run = db.query(ApifoxRun).filter(ApifoxRun.id == events[0]["run_id"]).first()

    assert run.parent_run_id is None

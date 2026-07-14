"""P-C 场景运行配置 · 外层迭代解析 / 持久化往返 / 数据驱动执行。

被测：
- run_service._resolve_scenario_iterations（循环次数 / 绑数据集 → 外层迭代列表）
- scenario_service 的 run_config 读写往返与绑定校验
- iter_scenario_run 数据驱动整场景（步骤数 × 数据行数、每行注入独立 runtime）
"""

import json

import pytest

from app.models.apifox.dataset import ApifoxDatasetRow
from app.models.apifox.run import ApifoxRunStep
from app.routers.apifox.dataset_schemas import DatasetCreate, DatasetRowIn
from app.routers.apifox.scenario_schemas import (
    ScenarioCreate,
    ScenarioRunConfig,
    ScenarioUpdate,
    StepIn,
)
from app.services.apifox import dataset_service, run_engine, run_service
from app.services.apifox import scenario_service as svc


def _scenario(db, steps=None):
    out = svc.create_scenario(db, project_id=1, data=ScenarioCreate(name="s", steps=steps or []))
    return svc.repo.get_scenario(db, out.id)


def _set_run_config(db, scenario, **cfg):
    scenario.run_config = json.dumps(cfg, ensure_ascii=False)
    db.commit()


def _dataset(db, rows, project_id=1, name="ds"):
    return dataset_service.create_dataset(
        db, project_id, DatasetCreate(name=name, columns=["user"], rows=rows)
    )


# ---- _resolve_scenario_iterations：循环次数 ----

def test_no_run_config_yields_single_empty_iteration(db):
    scenario = _scenario(db)

    assert run_service._resolve_scenario_iterations(db, scenario) == [{}]


def test_loop_count_yields_n_empty_iterations(db):
    scenario = _scenario(db)
    _set_run_config(db, scenario, loop_count=3)

    assert run_service._resolve_scenario_iterations(db, scenario) == [{}, {}, {}]


def test_loop_count_capped_at_max_iterations(db):
    scenario = _scenario(db)
    _set_run_config(db, scenario, loop_count=run_engine.MAX_LOOP_ITERATIONS + 500)

    assert len(run_service._resolve_scenario_iterations(db, scenario)) == run_engine.MAX_LOOP_ITERATIONS


def test_non_numeric_loop_count_falls_back_to_single(db):
    scenario = _scenario(db)
    _set_run_config(db, scenario, loop_count="abc")

    assert run_service._resolve_scenario_iterations(db, scenario) == [{}]


# ---- _resolve_scenario_iterations：绑数据集 ----

def test_dataset_binding_injects_each_enabled_row(db):
    ds = _dataset(db, rows=[
        DatasetRowIn(values={"user": "a"}),
        DatasetRowIn(values={"user": "b"}, enabled=False),
        DatasetRowIn(values={"user": "c"}),
    ])
    scenario = _scenario(db)
    _set_run_config(db, scenario, dataset_id=ds.id)

    injections = run_service._resolve_scenario_iterations(db, scenario)

    assert injections == [{"user": "a"}, {"user": "c"}]


def test_dataset_row_values_coerced_to_str(db):
    ds = _dataset(db, rows=[DatasetRowIn(values={"user": "a"})])
    # 直插非字符串值，验证防御性 str 强转（None→""、数字→字符串）
    db.add(ApifoxDatasetRow(dataset_id=ds.id, values=json.dumps({"age": 7, "note": None}), sort_order=1))
    db.commit()
    scenario = _scenario(db)
    _set_run_config(db, scenario, dataset_id=ds.id)

    injections = run_service._resolve_scenario_iterations(db, scenario)

    assert injections == [{"user": "a"}, {"age": "7", "note": ""}]


def test_dataset_from_other_project_falls_back_to_single(db):
    ds = _dataset(db, rows=[DatasetRowIn(values={"user": "a"})], project_id=2)
    scenario = _scenario(db)  # project_id=1
    _set_run_config(db, scenario, dataset_id=ds.id)

    assert run_service._resolve_scenario_iterations(db, scenario) == [{}]


def test_dataset_with_no_enabled_rows_falls_back_to_single(db):
    ds = _dataset(db, rows=[DatasetRowIn(values={"user": "a"}, enabled=False)])
    scenario = _scenario(db)
    _set_run_config(db, scenario, dataset_id=ds.id)

    assert run_service._resolve_scenario_iterations(db, scenario) == [{}]


def test_nonexistent_dataset_falls_back_to_single(db):
    scenario = _scenario(db)
    _set_run_config(db, scenario, dataset_id=99999)

    assert run_service._resolve_scenario_iterations(db, scenario) == [{}]


# ---- run_config 持久化往返 + 绑定校验 ----

def test_run_config_persisted_and_returned(db):
    ds = _dataset(db, rows=[DatasetRowIn(values={"user": "a"})])
    scenario = _scenario(db)

    out = svc.update_scenario(
        db, scenario,
        ScenarioUpdate(run_config=ScenarioRunConfig(loop_count=5, dataset_id=ds.id)),
    )

    assert out.run_config.loop_count == 5
    assert out.run_config.dataset_id == ds.id


def test_default_run_config_when_unset(db):
    out = svc.get_scenario_out(db, _scenario(db))

    assert out.run_config.loop_count == 1
    assert out.run_config.dataset_id is None


def test_binding_cross_project_dataset_rejected(db):
    ds = _dataset(db, rows=[DatasetRowIn(values={"user": "a"})], project_id=2)
    scenario = _scenario(db)

    with pytest.raises(ValueError, match="不属于本项目"):
        svc.update_scenario(db, scenario, ScenarioUpdate(run_config=ScenarioRunConfig(dataset_id=ds.id)))


# ---- 数据驱动整场景执行 ----

def test_data_driven_scenario_runs_steps_times_rows(db, make_case, monkeypatch):
    seen_vars = []

    def _fake(db, case, endpoint, environment, variables, assertions, extracts):
        seen_vars.append(dict(variables))
        return "passed", {"method": endpoint.method, "url": endpoint.path, "extracted": {}, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)

    case = make_case(name="c")
    ds = _dataset(db, rows=[DatasetRowIn(values={"user": "a"}), DatasetRowIn(values={"user": "b"})])
    scenario = _scenario(db, steps=[StepIn(type="case", ref_case_id=case.id)])
    _set_run_config(db, scenario, dataset_id=ds.id)

    events = list(run_service.iter_scenario_run(db, scenario, None, "test", user_id=1))

    run_id = events[0]["run_id"]
    steps = db.query(ApifoxRunStep).filter(ApifoxRunStep.run_id == run_id).all()
    assert events[0]["total"] == 2  # 1 步 × 2 行
    assert len(steps) == 2
    assert [v.get("user") for v in seen_vars] == ["a", "b"]


def test_scenario_binding_counts_toward_dataset_ref_and_blocks_delete(db):
    # 回归：场景 run_config 绑定数据集应计入引用计数，删除被拦截（评审 #1）
    ds = _dataset(db, rows=[DatasetRowIn(values={"user": "a"})])
    scenario = _scenario(db)
    svc.update_scenario(db, scenario, ScenarioUpdate(run_config=ScenarioRunConfig(dataset_id=ds.id)))

    briefs = {b.id: b for b in dataset_service.list_datasets(db, project_id=1)}
    assert briefs[ds.id].ref_count == 1

    with pytest.raises(ValueError, match="引用"):
        dataset_service.delete_dataset(db, dataset_service.repo.get_dataset(db, ds.id))


def test_iteration_failure_writes_failed_terminal_state(db, make_case, monkeypatch):
    # 回归：迭代中途未预期异常不得让运行永久卡 running（评审 #2，并发硬规则）
    def _boom(db, case, endpoint, environment, variables, assertions, extracts):
        raise RuntimeError("boom")

    monkeypatch.setattr(run_engine, "execute_case", _boom)

    case = make_case(name="c")
    scenario = _scenario(db, steps=[StepIn(type="case", ref_case_id=case.id)])
    _set_run_config(db, scenario, loop_count=3)

    gen = run_service.iter_scenario_run(db, scenario, None, "test", user_id=1)
    start = next(gen)
    with pytest.raises(RuntimeError):
        list(gen)

    from app.repositories.apifox import run_repo
    run = run_repo.get_run(db, start["run_id"])
    assert run.status == "failed"
    assert run.finished_at is not None


def test_each_data_row_gets_isolated_runtime(db, make_case, monkeypatch):
    # 第一行注入的变量不得残留到第二行（每行独立 runtime）
    seen_vars = []

    def _fake(db, case, endpoint, environment, variables, assertions, extracts):
        seen_vars.append(dict(variables))
        return "passed", {"method": endpoint.method, "url": endpoint.path, "extracted": {}, "scoped": []}

    monkeypatch.setattr(run_engine, "execute_case", _fake)

    case = make_case(name="c")
    ds = _dataset(db, rows=[DatasetRowIn(values={"only_first": "x"}), DatasetRowIn(values={"user": "b"})])
    scenario = _scenario(db, steps=[StepIn(type="case", ref_case_id=case.id)])
    _set_run_config(db, scenario, dataset_id=ds.id)

    list(run_service.iter_scenario_run(db, scenario, None, "test", user_id=1))

    assert "only_first" not in seen_vars[1]

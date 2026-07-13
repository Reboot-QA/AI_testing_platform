"""场景「数据库操作」步骤 · 校验 + 执行接入（提取/插值/失败隔离/连接归属）。

被测：scenario_service（db 步骤校验）+ run_service._run_db_step。db_executor.run_sql 打桩，
不连真实数据库——只验证编排、变量提取与落库。
"""

import json

import pytest

from app.models.apifox.database_conn import ApifoxEnvironmentDatabase
from app.models.apifox.run import ApifoxRunStep
from app.models.apifox.variable import ApifoxEnvironment
from app.routers.apifox.scenario_schemas import ScenarioCreate, StepIn
from app.services.apifox import db_executor, run_service
from app.services.apifox import scenario_service as ss


def _env_and_conn(db, project_id=1, env_name="dev", conn_name="devdb"):
    env = ApifoxEnvironment(project_id=project_id, name=env_name)
    db.add(env)
    db.commit()
    db.refresh(env)
    conn = ApifoxEnvironmentDatabase(environment_id=env.id, name=conn_name, host="h", database="d")
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return env, conn


def _db_step(conn_id, sql, extracts=None):
    return StepIn(type="db", name="DB", config={"connection_id": conn_id, "sql": sql, "extracts": extracts or []})


def _run(db, scenario_out, env):
    scenario = ss.repo.get_scenario(db, scenario_out.id)
    events = list(
        run_service.iter_scenario_run(db, scenario, environment=env, triggered_by="t", user_id=1)
    )
    steps = (
        db.query(ApifoxRunStep)
        .filter(ApifoxRunStep.run_id == events[0]["run_id"])
        .order_by(ApifoxRunStep.id)
        .all()
    )
    return events, steps


@pytest.fixture
def stub_ok(monkeypatch):
    monkeypatch.setattr(
        db_executor, "run_sql",
        lambda c, sql: {"passed": True, "columns": ["id"], "rows": [{"id": 7}], "rowcount": 1, "error": None},
    )


# ---------- 校验 ----------
def test_db_step_missing_connection_rejected(db):
    with pytest.raises(ValueError, match="数据库连接"):
        ss.create_scenario(db, 1, ScenarioCreate(
            name="s", steps=[StepIn(type="db", config={"sql": "SELECT 1"})]))


def test_db_step_missing_sql_rejected(db):
    _env, conn = _env_and_conn(db)
    with pytest.raises(ValueError, match="SQL"):
        ss.create_scenario(db, 1, ScenarioCreate(
            name="s", steps=[StepIn(type="db", config={"connection_id": conn.id, "sql": "  "})]))


def test_db_step_non_int_connection_id_rejected(db):
    """回归(评审#1)：非数字 connection_id 必须保存时拒绝，避免运行期 int() 抛异常卡 running。"""
    with pytest.raises(ValueError, match="数据库连接"):
        ss.create_scenario(db, 1, ScenarioCreate(
            name="s", steps=[StepIn(type="db", config={"connection_id": "abc", "sql": "SELECT 1"})]))


# ---------- 执行 ----------
def test_db_step_records_passed(db, stub_ok):
    env, conn = _env_and_conn(db)
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[_db_step(conn.id, "SELECT 1")]))

    _events, steps = _run(db, out, env)

    assert [s.step_type for s in steps] == ["db"]
    assert steps[0].status == "passed"


def test_db_step_extracts_first_row_column_to_variable(db, monkeypatch):
    env, conn = _env_and_conn(db)
    monkeypatch.setattr(
        db_executor, "run_sql",
        lambda c, sql: {"passed": True, "columns": ["uid"], "rows": [{"uid": 99}], "rowcount": 1, "error": None},
    )
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[
        _db_step(conn.id, "SELECT uid", [{"var_name": "myid", "column": "uid", "scope": "temporary"}]),
    ]))

    _events, steps = _run(db, out, env)

    ext = json.loads(steps[0].extract_results)
    assert ext[0]["var_name"] == "myid"
    assert ext[0]["value"] == "99"
    assert ext[0]["passed"] is True


def test_db_step_interpolates_sql_with_variables(db, monkeypatch):
    env, conn = _env_and_conn(db)
    seen = {}

    def fake(c, sql):
        seen["sql"] = sql
        return {"passed": True, "columns": ["v"], "rows": [{"v": "1"}], "rowcount": 1, "error": None}

    monkeypatch.setattr(db_executor, "run_sql", fake)
    # 先用一个 db 步骤把变量提取到 runtime，再在下一步 SQL 里插值
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[
        _db_step(conn.id, "SELECT 1", [{"var_name": "uid", "column": "v", "scope": "temporary"}]),
        _db_step(conn.id, "DELETE FROM t WHERE id={{uid}}"),
    ]))

    _run(db, out, env)

    assert seen["sql"] == "DELETE FROM t WHERE id=1"  # {{uid}} 被前步提取值替换


def test_db_step_failed_result_marks_failed(db, monkeypatch):
    env, conn = _env_and_conn(db)
    monkeypatch.setattr(
        db_executor, "run_sql",
        lambda c, sql: {"passed": False, "columns": [], "rows": [], "rowcount": 0, "error": "syntax error"},
    )
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[_db_step(conn.id, "BAD SQL")]))

    _events, steps = _run(db, out, env)

    assert steps[0].status == "failed"
    assert "syntax error" in (steps[0].error_message or "")


def test_db_step_connection_not_in_current_env_fails(db, stub_ok):
    env, _conn = _env_and_conn(db)
    _other_env, other_conn = _env_and_conn(db, env_name="prod", conn_name="proddb")
    # 用 dev 环境跑，却引用 prod 环境的连接 → 失败隔离
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[_db_step(other_conn.id, "SELECT 1")]))

    _events, steps = _run(db, out, env)

    assert steps[0].status == "failed"
    assert "环境" in (steps[0].error_message or "")

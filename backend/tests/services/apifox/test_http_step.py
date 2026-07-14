"""场景「裸 HTTP 请求」步骤 · 校验 + 执行接入（发送/断言/提取/失败）。

被测：scenario_service（http 步骤校验）+ run_service._run_http_step。
engine.execute_http_request 打桩，不发真实请求——只验证编排、变量提取与落库。
"""

import json

import pytest

from app.models.apifox.run import ApifoxRunStep
from app.routers.apifox.scenario_schemas import ScenarioCreate, StepIn
from app.services.apifox import run_engine, run_service
from app.services.apifox import scenario_service as ss


def _http_step(method="GET", path="/x", assertions=None, extracts=None):
    return StepIn(type="http", name="HTTP", config={
        "method": method, "path": path, "request_spec": {},
        "assertions": assertions or [], "extracts": extracts or [],
    })


def _run(db, scenario_out):
    scenario = ss.repo.get_scenario(db, scenario_out.id)
    events = list(run_service.iter_scenario_run(db, scenario, environment=None, triggered_by="t", user_id=1))
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
        run_engine, "execute_http_request",
        lambda *a, **k: ("passed", {"method": "GET", "url": "/x", "response_status": 200,
                                    "assertion_results": [], "extract_results": [], "extracted": {}, "scoped": []}),
    )


# ---------- 校验 ----------
def test_http_step_missing_method_rejected(db):
    with pytest.raises(ValueError, match="请求方法"):
        ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[StepIn(type="http", config={"path": "/a"})]))


def test_http_step_missing_path_rejected(db):
    with pytest.raises(ValueError, match="路径"):
        ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[StepIn(type="http", config={"method": "GET"})]))


# ---------- 执行 ----------
def test_http_step_records_passed(db, stub_ok):
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[_http_step("POST", "/login")]))

    _events, steps = _run(db, out)

    assert [s.step_type for s in steps] == ["http"]
    assert steps[0].status == "passed"


def test_http_step_extracts_to_runtime_for_next_step(db, monkeypatch):
    """裸步骤提取的变量须写入 runtime 供后续步骤 {{var}} 使用。"""
    seen = {}

    def fake(db_, pid, method, path, sn, spec, asserts, extracts, env, variables):
        if path == "/login":
            return "passed", {"method": method, "url": path, "extracted": {"tok": "abc"},
                              "extract_results": [], "assertion_results": [], "scoped": []}
        seen["tok"] = variables.get("tok")  # 第二步应看到上一步提取的 tok
        return "passed", {"method": method, "url": path, "extracted": {}, "extract_results": [],
                          "assertion_results": [], "scoped": []}

    monkeypatch.setattr(run_engine, "execute_http_request", fake)
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[
        _http_step("POST", "/login", extracts=[{"var_name": "tok", "source": "response_json", "path": "token"}]),
        _http_step("GET", "/me"),
    ]))

    _run(db, out)

    assert seen["tok"] == "abc"


def test_http_step_failed_result_marks_failed(db, monkeypatch):
    monkeypatch.setattr(
        run_engine, "execute_http_request",
        lambda *a, **k: ("failed", {"method": "GET", "url": "/x", "error_message": "请求失败: timeout",
                                    "assertion_results": [], "extract_results": [], "extracted": {}, "scoped": []}),
    )
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[_http_step()]))

    _events, steps = _run(db, out)

    assert steps[0].status == "failed"
    assert "timeout" in (steps[0].error_message or "")


def test_http_step_non_int_assertion_config_marks_failed_not_running(db):
    """回归(评审#1)：脏断言/提取配置须转失败态，不得抛异常让 run 卡 running。"""
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[
        StepIn(type="http", name="bad", config={
            "method": "GET", "path": "/x",
            "extracts": [{"source": "response_json"}],  # 缺必填 var_name → pydantic 会拒
        }),
    ]))

    events, steps = _run(db, out)

    assert steps[0].status == "failed"
    assert "配置无效" in (steps[0].error_message or "")
    from app.models.apifox.run import ApifoxRun
    run = db.query(ApifoxRun).filter(ApifoxRun.id == events[0]["run_id"]).first()
    assert run.status == "failed"  # run 落终态，未卡 running


# ---------- execute_http_request 本体（mock httpx，不打桩被测函数） ----------
def test_execute_http_request_success(db, monkeypatch):
    """评审#3：不打桩本体，mock httpx.Client.request 验证请求成功 + 断言/提取写入 detail。"""
    import httpx

    from app.routers.apifox.case_schemas import AssertionRow as AR
    from app.routers.apifox.case_schemas import ExtractRow as ER
    from app.services.apifox import run_engine

    class _Resp:
        status_code = 200
        headers = {"Content-Type": "application/json"}
        text = '{"token": "abc"}'

        def json(self):
            return json.loads(self.text)

    monkeypatch.setattr(httpx.Client, "request", lambda self, *a, **k: _Resp())

    status, detail = run_engine.execute_http_request(
        db, 1, "GET", "https://api.example.com/x", None, {},
        [AR(type="status_code", operator="eq", expected="200")],
        [ER(var_name="tok", source="response_json", path="token", scope="temporary")],
        None, {},
    )

    assert status == "passed"
    assert detail["response_status"] == 200
    assert detail["extracted"].get("tok") == "abc"


def test_execute_http_request_build_error_returns_failed(db):
    """build_request 抛 ValueError（相对路径 + 无环境）→ failed，不外抛。"""
    from app.services.apifox import run_engine

    status, detail = run_engine.execute_http_request(
        db, 1, "GET", "/relative/path", None, {}, [], [], None, {},
    )

    assert status == "failed"
    assert detail["error_message"]


def test_execute_http_request_network_error_returns_failed(db, monkeypatch):
    import httpx

    from app.services.apifox import run_engine

    def _boom(self, *a, **k):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.Client, "request", _boom)

    status, detail = run_engine.execute_http_request(
        db, 1, "GET", "https://api.example.com/x", None, {}, [], [], None, {},
    )

    assert status == "failed"
    assert "请求失败" in (detail["error_message"] or "")


def test_http_step_assertion_results_recorded(db, monkeypatch):
    monkeypatch.setattr(
        run_engine, "execute_http_request",
        lambda *a, **k: ("passed", {"method": "GET", "url": "/x",
                                    "assertion_results": [{"passed": True, "message": "状态码=200"}],
                                    "extract_results": [], "extracted": {}, "scoped": []}),
    )
    out = ss.create_scenario(db, 1, ScenarioCreate(name="s", steps=[
        _http_step(assertions=[{"type": "status_code", "operator": "eq", "expected": "200"}]),
    ]))

    _events, steps = _run(db, out)

    assert json.loads(steps[0].assertion_results)[0]["passed"] is True

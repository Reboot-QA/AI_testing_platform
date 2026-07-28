"""有序处理器 · 引擎按序执行（阶段2）。mock _send_request 避免真实网络。

覆盖：断言 op、提取 op、无断言 op 时默认 2xx 校验；有处理器才走新路径（旧路径零回归见既有测试）。
"""

import json
import shutil

import httpx
import pytest

from app.models.apifox.database_conn import ApifoxEnvironmentDatabase
from app.models.apifox.variable import ApifoxEnvironment

# 先加载 routers.apifox 包，规避直接 import run_engine 触发的既有潜在循环导入（同 test_run_service）
from app.routers.apifox import case_schemas  # noqa: F401
from app.services.apifox import db_executor, run_engine


def _resp(status=200, body='{"token":"abc"}'):
    return httpx.Response(
        status, content=body.encode(),
        headers={"Content-Type": "application/json"},
        request=httpx.Request("GET", "http://x/"),
    )


@pytest.fixture
def stub_send(monkeypatch):
    def _install(resp):
        def _fake(plan, detail, **kw):
            detail["duration_ms"] = 1.0
            return resp
        monkeypatch.setattr(run_engine, "_send_request", _fake)
    return _install


def _run(db, case, endpoint):
    return run_engine.execute_case(db, case, endpoint, None, {}, [], [])


def test_assertion_op_pass_and_fail(db, make_case, stub_send):
    case = make_case()
    from app.models.apifox.endpoint import ApifoxEndpoint

    ep = db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == case.endpoint_id).first()
    ep.path = "http://t.local/x"  # 绝对地址，build_request 无需环境
    case.post_processors = json.dumps(
        [{"kind": "assertion", "type": "status_code", "operator": "eq", "expected": "200"}]
    )

    stub_send(_resp(200))
    status, _ = _run(db, case, ep)
    assert status == "passed"

    stub_send(_resp(500))
    status, _ = _run(db, case, ep)
    assert status == "failed"


def test_extract_op_populates_extracted(db, make_case, stub_send):
    case = make_case()
    from app.models.apifox.endpoint import ApifoxEndpoint

    ep = db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == case.endpoint_id).first()
    ep.path = "http://t.local/x"  # 绝对地址，build_request 无需环境
    case.post_processors = json.dumps(
        [{"kind": "extract", "var_name": "tk", "source": "response_json", "path": "$.token", "scope": "temporary"}]
    )

    stub_send(_resp(200, '{"token":"abc"}'))
    status, detail = _run(db, case, ep)

    assert detail["extracted"].get("tk") == "abc"
    assert status == "passed"  # 无断言 op → 默认 2xx 校验通过


def test_pre_wait_op_sleeps(db, make_case, stub_send, monkeypatch):
    """前置 wait 处理器在单用例执行时真正 sleep（复现「等待无效」的对照：case 运行路径正常）。"""
    case = make_case()
    from app.models.apifox.endpoint import ApifoxEndpoint

    ep = db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == case.endpoint_id).first()
    ep.path = "http://t.local/x"
    case.pre_processors = json.dumps([{"kind": "wait", "wait_ms": 5000}])

    sleeps: list[float] = []
    monkeypatch.setattr(run_engine.time, "sleep", lambda s: sleeps.append(s))
    stub_send(_resp(200))
    status, _ = _run(db, case, ep)

    assert status == "passed"
    assert 5.0 in sleeps  # 5000ms → time.sleep(5.0)


def test_no_assertion_op_defaults_to_2xx(db, make_case, stub_send):
    case = make_case()
    from app.models.apifox.endpoint import ApifoxEndpoint

    ep = db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == case.endpoint_id).first()
    ep.path = "http://t.local/x"  # 绝对地址，build_request 无需环境
    # 只有提取、无断言：默认 2xx/3xx 校验 → 500 应判失败
    case.post_processors = json.dumps(
        [{"kind": "extract", "var_name": "tk", "source": "response_json", "path": "$.token"}]
    )

    stub_send(_resp(500))
    status, _ = _run(db, case, ep)
    assert status == "failed"


# ---------- 内联脚本（script_inline）：正文直接存步骤，运行时不查脚本库 ----------
def _abs_ep(db, case):
    from app.models.apifox.endpoint import ApifoxEndpoint

    ep = db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == case.endpoint_id).first()
    ep.path = "http://t.local/x"  # 绝对地址，build_request 无需环境
    return ep


def test_script_inline_post_python_reads_response(db, make_case, stub_send):
    """后置内联 Python 脚本可读响应上下文，日志入 script_logs；无断言 op → 默认 2xx 通过。"""
    case = make_case()
    ep = _abs_ep(db, case)
    case.post_processors = json.dumps(
        [{"kind": "script_inline", "script_lang": "python", "content": 'print("seen", response_status)'}]
    )

    stub_send(_resp(200))
    status, detail = _run(db, case, ep)

    assert status == "passed"
    assert any("[内联脚本] seen 200" in line for line in detail["script_logs"])


def test_script_inline_pre_and_post_python_chain_variable(db, make_case, stub_send):
    """前置内联写变量 → 后置内联读同一变量，验证内联脚本与变量串联同时生效。"""
    case = make_case()
    ep = _abs_ep(db, case)
    case.pre_processors = json.dumps(
        [{"kind": "script_inline", "script_lang": "python", "content": 'variables["greet"] = "hi"'}]
    )
    case.post_processors = json.dumps(
        [{"kind": "script_inline", "script_lang": "python", "content": 'print("got", variables.get("greet"))'}]
    )

    stub_send(_resp(200))
    status, detail = _run(db, case, ep)

    assert status == "passed"
    assert any("[内联脚本] got hi" in line for line in detail["script_logs"])


def test_script_inline_post_python_error_logged_not_crash(db, make_case, stub_send):
    """后置内联脚本报错只记录到 script_logs，不使流程崩溃（对齐库引用后置脚本 error 语义）。"""
    case = make_case()
    ep = _abs_ep(db, case)
    case.post_processors = json.dumps(
        [{"kind": "script_inline", "script_lang": "python", "content": "x = 1 / 0"}]
    )

    stub_send(_resp(200))
    status, detail = _run(db, case, ep)

    assert status == "passed"  # 后置脚本 error 不拉低状态
    assert any("内联脚本错误" in line for line in detail["script_logs"])


def test_script_inline_pre_python_error_fails_case(db, make_case, stub_send):
    """前置内联脚本报错短路整用例（对齐前置脚本失败语义）。"""
    case = make_case()
    ep = _abs_ep(db, case)
    case.pre_processors = json.dumps(
        [{"kind": "script_inline", "script_lang": "python", "content": "x = 1 / 0"}]
    )

    stub_send(_resp(200))
    status, detail = _run(db, case, ep)

    assert status == "failed"
    assert "前置脚本失败" in (detail["error_message"] or "")


@pytest.mark.skipif(shutil.which("node") is None, reason="需要本机 node 才能跑 JS 脚本")
def test_script_inline_post_js_reads_response(db, make_case, stub_send):
    """后置内联 JS 脚本走 pm.* 兼容层读响应并断言，pm.test 日志入 script_logs。"""
    case = make_case()
    ep = _abs_ep(db, case)
    case.post_processors = json.dumps(
        [
            {
                "kind": "script_inline",
                "script_lang": "javascript",
                "content": 'pm.test("code=200", () => pm.expect(pm.response.code).to.equal(200));',
            }
        ]
    )

    stub_send(_resp(200))
    status, detail = _run(db, case, ep)

    assert status == "passed"
    assert any("✓ code=200" in line for line in detail["script_logs"])


# ---------- 数据库操作（database）：环境级连接 + SQL + 首行提取 ----------
def _env_and_conn(db, project_id, env_name="dev", conn_name="devdb"):
    env = ApifoxEnvironment(project_id=project_id, name=env_name)
    db.add(env)
    db.commit()
    db.refresh(env)
    conn = ApifoxEnvironmentDatabase(environment_id=env.id, name=conn_name, host="h", database="d")
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return env, conn


def _run_env(db, case, endpoint, environment):
    return run_engine.execute_case(db, case, endpoint, environment, {}, [], [])


@pytest.fixture
def stub_run_sql(monkeypatch):
    def _install(result):
        monkeypatch.setattr(db_executor, "run_sql", lambda conn, sql: result)
    return _install


def test_db_op_pre_extracts_variable(db, make_case, stub_send, stub_run_sql):
    """前置数据库操作：执行 SQL、从结果首行提取列到变量（写入 detail.extracted）。"""
    case = make_case()
    ep = _abs_ep(db, case)
    env, conn = _env_and_conn(db, case.project_id)
    stub_run_sql({"passed": True, "columns": ["uid"], "rows": [{"uid": 99}], "rowcount": 1, "error": None})
    case.pre_processors = json.dumps([{
        "kind": "database", "connection_id": conn.id, "sql": "SELECT uid",
        "db_extracts": [{"var_name": "myid", "column": "uid", "scope": "temporary"}],
    }])

    stub_send(_resp(200))
    status, detail = _run_env(db, case, ep, env)

    assert status == "passed"
    assert detail["extracted"].get("myid") == "99"


def test_db_op_post_extracts_variable(db, make_case, stub_send, stub_run_sql):
    """后置数据库操作：无断言 → 默认 2xx 通过，且变量被提取。"""
    case = make_case()
    ep = _abs_ep(db, case)
    env, conn = _env_and_conn(db, case.project_id)
    stub_run_sql({"passed": True, "columns": ["cnt"], "rows": [{"cnt": 3}], "rowcount": 1, "error": None})
    case.post_processors = json.dumps([{
        "kind": "database", "connection_id": conn.id, "sql": "SELECT count(*) cnt",
        "db_extracts": [{"var_name": "total", "column": "cnt", "scope": "temporary"}],
    }])

    stub_send(_resp(200))
    status, detail = _run_env(db, case, ep, env)

    assert status == "passed"
    assert detail["extracted"].get("total") == "3"


def test_db_op_pre_failure_fails_case(db, make_case, stub_send, stub_run_sql):
    """前置数据库操作 SQL 失败 → 短路整用例失败。"""
    case = make_case()
    ep = _abs_ep(db, case)
    env, conn = _env_and_conn(db, case.project_id)
    stub_run_sql({"passed": False, "columns": [], "rows": [], "rowcount": 0, "error": "syntax error"})
    case.pre_processors = json.dumps([{"kind": "database", "connection_id": conn.id, "sql": "BAD SQL"}])

    stub_send(_resp(200))
    status, detail = _run_env(db, case, ep, env)

    assert status == "failed"
    assert "数据库操作失败" in (detail["error_message"] or "")
    assert "syntax error" in (detail["error_message"] or "")


def test_db_op_connection_not_in_current_env_fails(db, make_case, stub_send, stub_run_sql):
    """引用的连接不属于当前环境 → 该操作失败（对齐场景 db 步骤的环境隔离）。"""
    case = make_case()
    ep = _abs_ep(db, case)
    env, _conn = _env_and_conn(db, case.project_id)
    _other_env, other_conn = _env_and_conn(db, case.project_id, env_name="prod", conn_name="proddb")
    stub_run_sql({"passed": True, "columns": [], "rows": [], "rowcount": 0, "error": None})
    # 用 dev 环境跑，却引用 prod 环境的连接
    case.pre_processors = json.dumps([{"kind": "database", "connection_id": other_conn.id, "sql": "SELECT 1"}])

    stub_send(_resp(200))
    status, detail = _run_env(db, case, ep, env)

    assert status == "failed"
    assert "环境" in (detail["error_message"] or "")


# ---------- 数据库脚本（database_script）：引用 SQL 脚本库，运行时取库最新 SQL ----------
def _sql_script(db, project_id, content, name="lib-sql"):
    from app.models.apifox.sql_script import ApifoxSqlScript

    s = ApifoxSqlScript(project_id=project_id, name=name, content=content)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_db_script_op_reads_library_sql_and_extracts(db, make_case, stub_send, monkeypatch):
    """database_script 取库最新 SQL 执行并支持 db_extracts。"""
    case = make_case()
    ep = _abs_ep(db, case)
    env, conn = _env_and_conn(db, case.project_id)
    script = _sql_script(db, case.project_id, "SELECT uid FROM t LIMIT 1")
    seen = {}

    def _capture(conn, sql):
        seen["sql"] = sql
        return {"passed": True, "columns": ["uid"], "rows": [{"uid": 7}], "rowcount": 1, "error": None}

    monkeypatch.setattr(db_executor, "run_sql", _capture)
    case.pre_processors = json.dumps([{
        "kind": "database_script", "connection_id": conn.id, "sql_script_id": script.id,
        "db_extracts": [{"var_name": "uid", "column": "uid", "scope": "temporary"}],
    }])

    stub_send(_resp(200))
    status, detail = _run_env(db, case, ep, env)

    assert status == "passed"
    assert detail["extracted"].get("uid") == "7"
    assert seen["sql"] == "SELECT uid FROM t LIMIT 1"  # 执行的是库里的 SQL


def test_db_script_op_missing_script_fails_case(db, make_case, stub_send, stub_run_sql):
    """引用的 SQL 脚本不存在（如已删）→ 前置短路失败。"""
    case = make_case()
    ep = _abs_ep(db, case)
    env, conn = _env_and_conn(db, case.project_id)
    stub_run_sql({"passed": True, "columns": [], "rows": [], "rowcount": 0, "error": None})
    case.pre_processors = json.dumps([{
        "kind": "database_script", "connection_id": conn.id, "sql_script_id": 88888,
    }])

    stub_send(_resp(200))
    status, detail = _run_env(db, case, ep, env)

    assert status == "failed"
    assert "SQL 脚本不存在" in (detail["error_message"] or "")

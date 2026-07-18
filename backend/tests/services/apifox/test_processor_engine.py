"""有序处理器 · 引擎按序执行（阶段2）。mock _send_request 避免真实网络。

覆盖：断言 op、提取 op、无断言 op 时默认 2xx 校验；有处理器才走新路径（旧路径零回归见既有测试）。
"""

import json

import httpx
import pytest

# 先加载 routers.apifox 包，规避直接 import run_engine 触发的既有潜在循环导入（同 test_run_service）
from app.routers.apifox import case_schemas  # noqa: F401
from app.services.apifox import run_engine


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

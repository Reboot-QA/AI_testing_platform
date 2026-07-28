"""用例运行只跑自身断言，不继承接口级断言（Confluence 7/23-#14 / A1）。

复现测试对照：接口上配了"成功路径"断言（status_code==200），
负向用例（返回 422、自身只断言 422==422）本该通过，
修复前会因继承接口断言被判失败、并多显示接口那几条。
"""

import json
from types import SimpleNamespace

import httpx
import pytest

from app.models.apifox.endpoint import ApifoxEndpoint, ApifoxEndpointAssertion

# 先加载 routers.apifox 包，规避直接 import run_engine 的潜在循环导入（同 test_processor_engine）
from app.routers.apifox import case_schemas  # noqa: F401
from app.services.apifox import run_engine


def _resp(status=422, body='{"detail":"Validation error"}'):
    return httpx.Response(
        status, content=body.encode(),
        headers={"Content-Type": "application/json"},
        request=httpx.Request("POST", "http://x/"),
    )


@pytest.fixture
def stub_send(monkeypatch):
    def _install(resp):
        def _fake(plan, detail, **kw):
            detail["duration_ms"] = 1.0
            return resp
        monkeypatch.setattr(run_engine, "_send_request", _fake)
    return _install


def _abs_ep_with_ep_assertion(db, case):
    """接口设绝对地址 + 一条会在 422 响应下失败的接口级断言（status_code==200）。"""
    ep = db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == case.endpoint_id).first()
    ep.path = "http://t.local/x"
    db.add(ApifoxEndpointAssertion(
        endpoint_id=ep.id, type="status_code", operator="eq", expected="200", enabled=True
    ))
    db.commit()
    return ep


def _case_own_422():
    """用例自身断言：status_code==422（在 422 响应下通过）。"""
    return SimpleNamespace(enabled=True, type="status_code", operator="eq", expected="422", path=None)


def test_legacy_path_ignores_endpoint_assertions(db, make_case, stub_send):
    case = make_case()
    ep = _abs_ep_with_ep_assertion(db, case)  # 接口级 status_code==200（会失败）

    stub_send(_resp(422))
    status, detail = run_engine.execute_case(db, case, ep, None, {}, [_case_own_422()], [])

    assert status == "passed"  # 只跑用例自身 422==422；修复前继承接口 200== 会判失败
    results = detail["assertion_results"]
    assert len(results) == 1  # 只显示用例自身一条，不含接口那条
    assert results[0]["expected"] == "422"


def test_processor_path_ignores_endpoint_assertions(db, make_case, stub_send):
    case = make_case()
    ep = _abs_ep_with_ep_assertion(db, case)
    case.post_processors = json.dumps(
        [{"kind": "assertion", "type": "status_code", "operator": "eq", "expected": "422"}]
    )

    stub_send(_resp(422))
    status, _ = run_engine.execute_case(db, case, ep, None, {}, [], [])

    assert status == "passed"  # 处理器路径同样不追加接口级断言

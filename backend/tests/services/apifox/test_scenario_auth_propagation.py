"""场景级登录态跨步骤透传 · cookie jar 共享 + 响应体 token 自动捕获/注入。

覆盖：token 字段识别、Authorization 手动优先且更新后续 token、_send_request 注入/捕获、
场景两步骤间 cookie+token 透传、关闭开关不透传、用例运行(=套件项)默认不透传。
"""

import json
from types import SimpleNamespace

import httpx
import pytest

from app.routers.apifox.scenario_schemas import (
    ScenarioCreate,
    ScenarioRunConfig,
    ScenarioUpdate,
    StepIn,
)
from app.services.apifox import run_engine, run_service
from app.services.apifox import scenario_service as ss

LOGIN = "https://api.example.com/login"
ME = "https://api.example.com/me"


# ---------- fakes ----------
class _FakeResp:
    def __init__(self, set_cookies=None, body=None):
        self.status_code = 200
        self.headers = {"Content-Type": "application/json"}
        self._body = body if body is not None else {}
        self.text = json.dumps(self._body)
        self.cookies = httpx.Cookies()
        for key, val in (set_cookies or {}).items():
            self.cookies.set(key, val)

    def json(self):
        return self._body


def _recorder(calls, resp_for):
    def _request(self, method, url, params=None, headers=None, cookies=None, **kwargs):
        calls.append({"url": url, "headers": dict(headers or {}), "cookies": cookies})
        return resp_for(url)

    return _request


def _http_step(path, method="GET"):
    return StepIn(type="http", name=path, config={"method": method, "path": path, "request_spec": {}})


def _run(db, scenario_out):
    scenario = ss.repo.get_scenario(db, scenario_out.id)
    return list(run_service.iter_scenario_run(db, scenario, None, "t", 1))


def _auth_of(call):
    return {k.lower(): v for k, v in call["headers"].items()}.get("authorization")


# ---------- 纯函数：token 字段识别 / Authorization 取值 ----------
@pytest.mark.parametrize(
    "headers,expected",
    [
        ({"Authorization": "Bearer abc"}, "abc"),
        ({"authorization": "Token xyz"}, None),  # 非 Bearer 不作为可转发 token
        ({"Authorization": "Basic zzz"}, None),
        ({"X-Other": "1"}, None),
    ],
)
def test_bearer_from_headers(headers, expected):
    assert run_engine._bearer_from_headers(headers) == expected


@pytest.mark.parametrize(
    "body,expected",
    [
        ({"token": "t1"}, "t1"),
        ({"access_token": "t2"}, "t2"),
        ({"data": {"token": "t3"}}, "t3"),  # 一层嵌套
        ({"result": {"jwt": "t4"}}, "t4"),
        ({"nope": "x"}, None),
        ({"token": ""}, None),  # 空串不算
    ],
)
def test_capture_token_from_body(body, expected):
    assert run_engine._capture_token_from_body(_FakeResp(body=body)) == expected


# ---------- _send_request：注入 / 捕获 / 手动优先 ----------
def _plan(headers=None):
    return {
        "method": "GET", "url": ME, "params": {}, "headers": headers or {},
        "body_snapshot": "", "request_kwargs": {}, "warnings": [],
    }


def test_send_request_injects_token_updates_jar_and_captures(db, monkeypatch):
    calls = []
    monkeypatch.setattr(
        httpx.Client, "request",
        _recorder(calls, lambda url: _FakeResp(set_cookies={"sid": "S1"}, body={"token": "NEW"})),
    )
    jar = httpx.Cookies()
    detail = {}

    run_engine._send_request(_plan(), detail, cookie_jar=jar, auth_token="OLD")

    assert _auth_of(calls[0]) == "Bearer OLD"  # 未显式设 → 自动注入现有 token
    assert jar.get("sid") == "S1"  # 响应 Set-Cookie 累积进 jar
    assert detail["captured_token"] == "NEW"  # 响应体新 token 供后续步骤


def test_send_request_manual_authorization_wins_and_becomes_forward_token(db, monkeypatch):
    calls = []
    monkeypatch.setattr(
        httpx.Client, "request", _recorder(calls, lambda url: _FakeResp(body={}))  # 响应体无 token
    )
    detail = {}

    run_engine._send_request(
        _plan(headers={"Authorization": "Bearer MANUAL"}), detail, auth_token="OLD"
    )

    assert _auth_of(calls[0]) == "Bearer MANUAL"  # 手动写死的不被覆盖
    assert detail["captured_token"] == "MANUAL"  # 手动值更新为后续传递 token


def test_send_request_no_jar_skips_cookie_and_injection(db, monkeypatch):
    calls = []
    monkeypatch.setattr(httpx.Client, "request", _recorder(calls, lambda url: _FakeResp(body={})))
    detail = {}

    run_engine._send_request(_plan(), detail)  # cookie_jar/auth_token 均 None

    assert calls[0]["cookies"] is None
    assert _auth_of(calls[0]) is None  # 关闭态：不注入


def test_send_request_non_bearer_manual_not_overridden_nor_forwarded(db, monkeypatch):
    calls = []
    monkeypatch.setattr(httpx.Client, "request", _recorder(calls, lambda url: _FakeResp(body={})))
    detail = {}

    run_engine._send_request(_plan(headers={"Authorization": "Token xyz"}), detail, auth_token="OLD")

    assert _auth_of(calls[0]) == "Token xyz"  # 手动非 Bearer 不被自动注入覆盖
    assert detail["captured_token"] is None  # 且不作为可转发 token（避免注成 "Bearer Token xyz"）


# ---------- 场景集成：跨步骤透传 ----------
def _login_then_me(db, monkeypatch, propagate):
    calls = []

    def resp_for(url):
        if url.endswith("/login"):
            return _FakeResp(set_cookies={"sid": "S1"}, body={"token": "T123"})
        return _FakeResp(body={})

    monkeypatch.setattr(httpx.Client, "request", _recorder(calls, resp_for))
    out = ss.create_scenario(db, 1, ScenarioCreate(
        name="s", steps=[_http_step(LOGIN, "POST"), _http_step(ME, "GET")],
    ))
    # run_config 仅 update 落库；缺字段=默认开，故只有关闭态需显式写入
    if not propagate:
        scenario = ss.repo.get_scenario(db, out.id)
        ss.update_scenario(db, scenario, ScenarioUpdate(run_config=ScenarioRunConfig(propagate_auth=False)))
    _run(db, out)
    return next(c for c in calls if c["url"].endswith("/me"))


def test_scenario_propagates_cookie_and_token_across_steps(db, monkeypatch):
    me_call = _login_then_me(db, monkeypatch, propagate=True)

    assert _auth_of(me_call) == "Bearer T123"  # 登录响应体 token 自动注入到第二步
    assert me_call["cookies"] is not None and me_call["cookies"].get("sid") == "S1"  # cookie 透传


def test_scenario_propagation_off_no_carry(db, monkeypatch):
    me_call = _login_then_me(db, monkeypatch, propagate=False)

    assert _auth_of(me_call) is None
    assert me_call["cookies"] is None


def test_run_context_defaults_to_no_propagation(db):
    """用例运行/套件项默认不透传的唯一依据：_RunContext.propagate_auth 缺省 False。"""
    ctx = run_service._RunContext(db, SimpleNamespace(id=1), None, None)

    assert ctx.propagate_auth is False
    assert ctx.propagation_kwargs() == {}  # 不透传时不向执行函数传 cookie_jar/auth_token

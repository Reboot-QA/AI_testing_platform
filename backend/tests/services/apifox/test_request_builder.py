"""request_builder 单元 · URL 拼接 / path_params / 认证 / 各 body 类型 / 全局参数 / 命名 server。"""

import base64
from types import SimpleNamespace

import pytest

from app.services.apifox.request_builder import _select_base_url, build_request


def _endpoint(*, path: str, method: str = "GET", server_name=None):
    return SimpleNamespace(path=path, method=method, server_name=server_name)


def _env(*, base_url: str = "", servers=None):
    return SimpleNamespace(base_url=base_url, servers=servers or [])


def _server(*, name: str, base_url: str):
    return SimpleNamespace(name=name, base_url=base_url)


def _global_param(*, key: str, value: str, location: str, enabled: bool = True):
    return SimpleNamespace(key=key, value=value, location=location, enabled=enabled)


def _build(endpoint, spec=None, environment=None, variables=None, global_params=None):
    return build_request(endpoint, spec or {}, environment, variables or {}, global_params or [])


# ---------- URL 拼接 ----------
def test_relative_path_joined_with_base_url():
    plan = _build(_endpoint(path="/users"), environment=_env(base_url="https://api.test"))

    assert plan["url"] == "https://api.test/users"


def test_absolute_path_used_directly_ignoring_base():
    plan = _build(_endpoint(path="http://x.test/ping"), environment=_env(base_url="https://api.test"))

    assert plan["url"] == "http://x.test/ping"


def test_path_params_replaced_with_interpolated_value():
    spec = {"path_params": [{"key": "id", "value": "{{uid}}"}]}
    plan = _build(_endpoint(path="/users/{id}"), spec=spec, environment=_env(base_url="https://api.test"), variables={"uid": "42"})

    assert plan["url"] == "https://api.test/users/42"


def test_relative_path_without_base_url_raises():
    with pytest.raises(ValueError):
        _build(_endpoint(path="/users"), environment=_env(base_url=""))


# ---------- _select_base_url ----------
def test_select_base_url_prefers_named_server():
    env = _env(base_url="https://default.test", servers=[_server(name="prod", base_url="https://prod.test/")])

    assert _select_base_url(env, "prod") == "https://prod.test"


def test_select_base_url_falls_back_to_default_when_server_missing():
    env = _env(base_url="https://default.test/", servers=[_server(name="prod", base_url="https://prod.test")])

    assert _select_base_url(env, "staging") == "https://default.test"


def test_select_base_url_none_environment_yields_empty():
    assert _select_base_url(None, "prod") == ""


# ---------- 参数组装 ----------
def test_query_and_headers_interpolated():
    spec = {"query": [{"key": "q", "value": "{{term}}"}], "headers": [{"key": "X-Tok", "value": "{{t}}"}]}
    plan = _build(_endpoint(path="/s"), spec=spec, environment=_env(base_url="https://api.test"), variables={"term": "cat", "t": "abc"})

    assert plan["params"] == {"q": "cat"}
    assert plan["headers"]["X-Tok"] == "abc"


def test_cookies_serialized_into_cookie_header():
    spec = {"cookies": [{"key": "sid", "value": "s1"}]}
    plan = _build(_endpoint(path="/s"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["headers"]["Cookie"] == "sid=s1"


# ---------- 全局参数 ----------
def test_global_param_added_when_absent():
    gp = [_global_param(key="X-Env", value="prod", location="header")]
    plan = _build(_endpoint(path="/s"), environment=_env(base_url="https://api.test"), global_params=gp)

    assert plan["headers"]["X-Env"] == "prod"


def test_global_param_does_not_override_existing_header():
    spec = {"headers": [{"key": "X-Env", "value": "explicit"}]}
    gp = [_global_param(key="X-Env", value="global", location="header")]
    plan = _build(_endpoint(path="/s"), spec=spec, environment=_env(base_url="https://api.test"), global_params=gp)

    assert plan["headers"]["X-Env"] == "explicit"


def test_disabled_global_param_skipped():
    gp = [_global_param(key="X-Off", value="v", location="header", enabled=False)]
    plan = _build(_endpoint(path="/s"), environment=_env(base_url="https://api.test"), global_params=gp)

    assert "X-Off" not in plan["headers"]


# ---------- 认证 ----------
def test_bearer_auth_sets_authorization_header():
    spec = {"auth": {"type": "bearer", "token": "{{tok}}"}}
    plan = _build(_endpoint(path="/s"), spec=spec, environment=_env(base_url="https://api.test"), variables={"tok": "xyz"})

    assert plan["headers"]["Authorization"] == "Bearer xyz"


def test_basic_auth_base64_encodes_credentials():
    spec = {"auth": {"type": "basic", "username": "u", "password": "p"}}
    plan = _build(_endpoint(path="/s"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["headers"]["Authorization"] == "Basic " + base64.b64encode(b"u:p").decode("ascii")


# ---------- body ----------
def test_json_body_sets_content_and_default_content_type():
    spec = {"body": {"type": "json", "raw": '{"a": {{v}}}'}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"), variables={"v": "1"})

    assert plan["request_kwargs"]["content"] == '{"a": 1}'
    assert plan["headers"]["Content-Type"] == "application/json"


def test_raw_body_does_not_force_json_content_type():
    spec = {"body": {"type": "raw", "raw": "plain"}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["request_kwargs"]["content"] == "plain"
    assert "Content-Type" not in plan["headers"]


def test_urlencoded_body_goes_to_data():
    spec = {"body": {"type": "urlencoded", "form": [{"key": "a", "value": "1"}]}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["request_kwargs"]["data"] == {"a": "1"}


def test_form_data_body_goes_to_files():
    spec = {"body": {"type": "form-data", "form": [{"key": "a", "value": "1"}]}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["request_kwargs"]["files"] == {"a": (None, "1")}

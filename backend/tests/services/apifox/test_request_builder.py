"""request_builder 单元 · URL 拼接 / path_params / 认证 / 各 body 类型 / 全局参数 / 命名 server。"""

import base64
import json
from types import SimpleNamespace

import pytest

from app.routers.apifox.schemas import RequestSpec
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


def test_form_data_conflicting_content_type_kept_and_warned():
    # 测试工具「所配即所发」：form-data 带 Content-Type: application/json 时**不改动**用户配置，
    # 原样发送（服务端会因类型不符报错，这是有效测试结果），仅给出诊断警告
    spec = {
        "headers": [{"key": "Content-Type", "value": "application/json"}],
        "body": {"type": "form-data", "form": [{"key": "username", "value": "admin"}]},
    }
    plan = _build(_endpoint(path="/login", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["headers"]["Content-Type"] == "application/json"  # 不被删/改，原样保留
    assert plan["request_kwargs"]["files"] == {"username": (None, "admin")}
    assert plan["warnings"] and "form-data" in plan["warnings"][0] and "application/json" in plan["warnings"][0]


def test_form_data_multipart_without_boundary_warns():
    # multipart/form-data 但缺 boundary 也是坏配置（httpx 不回填 boundary 到用户显式头）→ 诊断警告
    spec = {
        "headers": [{"key": "Content-Type", "value": "multipart/form-data"}],
        "body": {"type": "form-data", "form": [{"key": "a", "value": "1"}]},
    }
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["warnings"] and "boundary" in plan["warnings"][0]


def test_form_data_multipart_with_boundary_no_warning():
    spec = {
        "headers": [{"key": "Content-Type", "value": "multipart/form-data; boundary=xyz"}],
        "body": {"type": "form-data", "form": [{"key": "a", "value": "1"}]},
    }
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["warnings"] == []  # 类型对且有 boundary，不打扰


def test_form_data_without_content_type_no_warning():
    spec = {"body": {"type": "form-data", "form": [{"key": "a", "value": "1"}]}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert plan["warnings"] == []  # 无显式 Content-Type，httpx 自动生成正确 multipart，不打扰


def test_urlencoded_conflicting_content_type_kept_and_warned():
    spec = {
        "headers": [{"key": "content-type", "value": "application/json"}],
        "body": {"type": "urlencoded", "form": [{"key": "username", "value": "admin"}]},
    }
    plan = _build(_endpoint(path="/login", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    cts = [v for k, v in plan["headers"].items() if k.lower() == "content-type"]
    assert cts == ["application/json"]  # 用户配置原样保留，不被覆盖
    assert plan["warnings"] and "x-www-form-urlencoded" in plan["warnings"][0]


def test_xml_body_sets_xml_content_type_and_interpolates():
    spec = {"body": {"type": "xml", "raw": "<a>{{v}}</a>"}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"), variables={"v": "1"})

    assert plan["request_kwargs"]["content"] == "<a>1</a>"
    assert plan["headers"]["Content-Type"] == "application/xml"


def test_graphql_body_wraps_query_and_variables_as_json():
    spec = {"body": {"type": "graphql", "graphql_query": "query{u(id:{{id}}){name}}", "graphql_variables": '{"id": {{id}}}'}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"), variables={"id": "5"})

    assert json.loads(plan["request_kwargs"]["content"]) == {"query": "query{u(id:5){name}}", "variables": {"id": 5}}
    assert plan["headers"]["Content-Type"] == "application/json"


def test_graphql_invalid_variables_fall_back_to_empty_object():
    spec = {"body": {"type": "graphql", "graphql_query": "{ping}", "graphql_variables": "not json"}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert json.loads(plan["request_kwargs"]["content"]) == {"query": "{ping}", "variables": {}}


def test_binary_body_uses_loader_bytes_and_content_type():
    spec = {"body": {"type": "binary", "file_id": 7}}
    loader = lambda fid: (b"\x89PNG", "image/png") if fid == 7 else None  # noqa: E731
    plan = build_request(_endpoint(path="/s", method="POST"), spec, _env(base_url="https://api.test"), {}, [], binary_loader=loader)

    assert plan["request_kwargs"]["content"] == b"\x89PNG"
    assert plan["headers"]["Content-Type"] == "image/png"
    assert plan["body_snapshot"] == "<binary 4 bytes>"


def test_binary_body_without_loader_sends_no_content():
    spec = {"body": {"type": "binary", "file_id": 7}}
    plan = _build(_endpoint(path="/s", method="POST"), spec=spec, environment=_env(base_url="https://api.test"))

    assert "content" not in plan["request_kwargs"]


def test_binary_body_loader_miss_sends_no_content():
    spec = {"body": {"type": "binary", "file_id": 7}}
    plan = build_request(_endpoint(path="/s", method="POST"), spec, _env(base_url="https://api.test"), {}, [], binary_loader=lambda fid: None)

    assert "content" not in plan["request_kwargs"]


# ---------- request_spec 契约保真（防 pydantic 静默丢字段，回归评审阻塞项） ----------
def test_request_spec_preserves_cookies_and_graphql_fields():
    spec = RequestSpec(**{
        "cookies": [{"key": "sid", "value": "s1"}],
        "body": {"type": "graphql", "graphql_query": "{ping}", "graphql_variables": '{"a":1}',
                 "file_id": 9, "file_name": "a.bin"},
    })
    dumped = spec.model_dump()

    assert [c["key"] for c in dumped["cookies"]] == ["sid"]
    assert dumped["body"]["graphql_query"] == "{ping}"
    assert dumped["body"]["graphql_variables"] == '{"a":1}'
    assert dumped["body"]["file_id"] == 9
    assert dumped["body"]["file_name"] == "a.bin"


# ---------- 请求设置（超时 / SSL / 重定向）解析进 plan ----------
def test_settings_default_when_absent():
    plan = _build(_endpoint(path="http://x/y"))

    assert plan["timeout"] is None  # 由调用方回落平台默认
    assert plan["verify_ssl"] is True
    assert plan["follow_redirects"] is True


def test_settings_timeout_ms_converted_to_seconds():
    plan = _build(_endpoint(path="http://x/y"), {"settings": {"timeout_ms": 5000}})

    assert plan["timeout"] == 5.0


@pytest.mark.parametrize("bad", [0, -1, "abc", None])
def test_settings_nonpositive_or_invalid_timeout_falls_back_none(bad):
    plan = _build(_endpoint(path="http://x/y"), {"settings": {"timeout_ms": bad}})

    assert plan["timeout"] is None


def test_settings_verify_ssl_and_redirects_passthrough():
    spec = {"settings": {"verify_ssl": False, "follow_redirects": False}}
    plan = _build(_endpoint(path="http://x/y"), spec)

    assert plan["verify_ssl"] is False
    assert plan["follow_redirects"] is False

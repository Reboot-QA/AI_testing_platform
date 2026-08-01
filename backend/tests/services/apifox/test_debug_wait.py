"""接口调试直发 · wait 处理器执行（复现 bug：调试时前置「等待」无效）。

调试走 debug_service.debug_send（旧分列字段路径），此前没有 wait 概念，导致前置等待被静默丢弃。
mock make_http_client 避免真实网络；mock time.sleep 断言等待被执行。
"""

import httpx

from app.routers.apifox import case_schemas  # noqa: F401  预加载规避潜在循环导入
from app.services.apifox import debug_service


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def request(self, *a, **k):
        return self._resp


def _resp():
    return httpx.Response(
        200, content=b'{"ok":true}',
        headers={"Content-Type": "application/json"},
        request=httpx.Request("GET", "http://t.local/x"),
    )


def _stub(monkeypatch):
    monkeypatch.setattr(debug_service.engine, "make_http_client", lambda plan: _FakeClient(_resp()))
    sleeps: list[float] = []
    monkeypatch.setattr(debug_service.time, "sleep", lambda s: sleeps.append(s))
    return sleeps


def test_debug_pre_wait_sleeps(db, monkeypatch):
    sleeps = _stub(monkeypatch)

    debug_service.debug_send(
        db, project_id=1, method="GET", path="http://t.local/x",
        request_spec={}, environment_id=None, user_id=1,
        pre_waits=[5000],
    )

    assert 5.0 in sleeps  # 前置等待 5000ms 应真正 sleep


def test_debug_post_wait_sleeps(db, monkeypatch):
    sleeps = _stub(monkeypatch)

    debug_service.debug_send(
        db, project_id=1, method="GET", path="http://t.local/x",
        request_spec={}, environment_id=None, user_id=1,
        post_waits=[1500],
    )

    assert 1.5 in sleeps


def test_debug_no_preurl_returns_error_not_raises(db):
    # 未配环境/前置 URL + 相对路径：返回带 error 的结果（不抛 400），响应区给一条提示即可（7/22-#12）
    result = debug_service.debug_send(
        db, project_id=1, method="GET", path="/relative",
        request_spec={}, environment_id=None, user_id=1,
    )

    assert result["status_code"] is None
    assert result["error"] and "前置 URL" in result["error"]

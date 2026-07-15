"""make_http_client 把请求计划的设置真正透传给 httpx.Client（WYSIWYG 关键环节）。"""

# 先导入 scenario_service，让 run_engine 以正确顺序完整加载：
# 否则以 run_engine 为孤立入口会触发 run_engine↔scenario_service 的既有循环导入。
import app.services.apifox.scenario_service  # noqa: F401
from app.services.apifox import run_engine as engine


def _capture_client_kwargs(monkeypatch) -> dict:
    captured: dict = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return kwargs  # 返回值不被使用，随便给

    monkeypatch.setattr(engine.httpx, "Client", fake_client)
    return captured


def test_make_http_client_passes_settings_through(monkeypatch):
    captured = _capture_client_kwargs(monkeypatch)

    engine.make_http_client({"timeout": 5.0, "verify_ssl": False, "follow_redirects": False})

    assert captured["timeout"] == 5.0
    assert captured["verify"] is False  # 关证书校验必须真正透传，不被默认 True 覆盖
    assert captured["follow_redirects"] is False


def test_make_http_client_falls_back_to_default_timeout(monkeypatch):
    captured = _capture_client_kwargs(monkeypatch)

    engine.make_http_client({"timeout": None, "verify_ssl": True, "follow_redirects": True})

    assert captured["timeout"] == engine.HTTP_TIMEOUT  # 未配超时回落平台默认
    assert captured["verify"] is True
    assert captured["follow_redirects"] is True


def test_make_http_client_defaults_when_keys_absent(monkeypatch):
    captured = _capture_client_kwargs(monkeypatch)

    engine.make_http_client({})  # plan 缺字段（历史/裸步骤）时用安全默认

    assert captured["timeout"] == engine.HTTP_TIMEOUT
    assert captured["verify"] is True
    assert captured["follow_redirects"] is True

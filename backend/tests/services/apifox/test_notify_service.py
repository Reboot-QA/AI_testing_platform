"""Apifox 通知 · service 集成测试（不触网，monkeypatch 发送）。

覆盖：配置读写(密钥不回传/留空保留/成功开关往返)、成功&失败开关矩阵门控、
import_schedule 复用定时开关(修复缺键 bug)、渠道错误不影响主流程、Telegram parse_mode。
"""

from app.routers.apifox.notify_schemas import NotifyConfigUpdate
from app.services.apifox import notify_service
from app.services.apifox.notify_templates import NotifyPayload

PID = 1


def _update(db, **kw):
    base = dict(
        email_enabled=True, smtp_host="smtp.x", smtp_port=465, smtp_username="u",
        email_recipients=["a@x.com"], notify_run=True,
    )
    base.update(kw)
    return notify_service.update_config(db, PID, NotifyConfigUpdate(**base))


def _payload(result="failure", event_type="run"):
    return NotifyPayload(
        event_type=event_type, result=result, project_name="P", scene="套件执行",
        target_name="T", total=5, passed=5 if result == "success" else 2,
        failed=0 if result == "success" else 3, ref_id=1,
    )


# ---------- 配置读写 ----------
def test_update_and_out_masks_secrets(db):
    _update(db, smtp_password="secret", telegram_enabled=True, telegram_bot_token="tok", telegram_chat_ids=["123"])

    out = notify_service.config_out(notify_service.notify_repo.get_by_project(db, PID))

    assert out.email_recipients == ["a@x.com"]
    assert out.smtp_password_set is True and out.telegram_bot_token_set is True
    assert not hasattr(out, "smtp_password")  # 密钥不回传


def test_blank_password_keeps_existing(db):
    _update(db, smtp_password="secret")

    _update(db, smtp_password=None)  # 再次保存不填密码

    cfg = notify_service.notify_repo.get_by_project(db, PID)
    assert cfg.smtp_password == "secret"  # 留空=保留原密钥


def test_success_switches_default_off_and_round_trip(db):
    _update(db)  # 未传成功开关

    out = notify_service.config_out(notify_service.notify_repo.get_by_project(db, PID))
    assert out.notify_run_success is False  # 成功通知默认关（opt-in）

    _update(db, notify_run_success=True, notify_schedule_success=True)

    out = notify_service.config_out(notify_service.notify_repo.get_by_project(db, PID))
    assert out.notify_run_success is True and out.notify_schedule_success is True
    assert out.notify_aigen_success is False


# ---------- 触发门控（成功/失败开关矩阵） ----------
def test_notify_event_noop_without_config(db):
    notify_service.notify_event(db, 999, _payload("failure"))  # 无配置，不抛异常


def test_failure_blocked_when_failure_switch_off(db, monkeypatch):
    _update(db, notify_run=False)
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda *a: sent.append(1))

    notify_service.notify_event(db, PID, _payload("failure"))

    assert sent == []


def test_failure_sent_when_failure_switch_on(db, monkeypatch):
    _update(db, notify_run=True)
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda cfg, subject, html, text: sent.append(subject))

    notify_service.notify_event(db, PID, _payload("failure"))

    assert len(sent) == 1 and "失败" in sent[0]


def test_success_blocked_when_success_switch_off(db, monkeypatch):
    _update(db, notify_run=True, notify_run_success=False)  # 失败开、成功关
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda *a: sent.append(1))

    notify_service.notify_event(db, PID, _payload("success"))

    assert sent == []  # 成功开关关，成功不发（即便失败开关开着）


def test_success_sent_when_success_switch_on(db, monkeypatch):
    _update(db, notify_run=False, notify_run_success=True)  # 失败关、成功开
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda cfg, subject, html, text: sent.append(subject))

    notify_service.notify_event(db, PID, _payload("success"))

    assert len(sent) == 1 and "成功" in sent[0]  # 成功与失败开关相互独立


def test_import_schedule_uses_schedule_switch(db, monkeypatch):
    _update(db, notify_schedule=True)  # 定时开关开
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda *a: sent.append(1))

    notify_service.notify_event(db, PID, _payload("failure", event_type="import_schedule"))

    assert sent == [1]  # import_schedule 复用 notify_schedule（修复原缺键从不发送的 bug）


def test_import_schedule_blocked_when_schedule_off(db, monkeypatch):
    _update(db, notify_schedule=False)
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda *a: sent.append(1))

    notify_service.notify_event(db, PID, _payload("failure", event_type="import_schedule"))

    assert sent == []


def test_channel_error_does_not_raise(db, monkeypatch):
    _update(db, notify_run=True)

    def boom(*a):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(notify_service, "send_email", boom)

    notify_service.notify_event(db, PID, _payload("failure"))  # 渠道报错不冒泡


# ---------- Telegram parse_mode ----------
def test_send_telegram_uses_html_parse_mode(db, monkeypatch):
    cfg = _update(db, telegram_enabled=True, telegram_bot_token="t", telegram_chat_ids=["1"])
    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

    class _Client:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, json=None):
            captured.update(json or {})
            return _Resp()

    monkeypatch.setattr(notify_service.httpx, "Client", _Client)

    notify_service.send_telegram(cfg, "<b>hi</b>")

    assert captured["parse_mode"] == "HTML" and captured["text"] == "<b>hi</b>"


# ---------- 测试发送 ----------
def test_test_config_sends_both_samples_and_reports(db, monkeypatch):
    cfg = _update(db, telegram_enabled=True, telegram_bot_token="t", telegram_chat_ids=["1"])
    email_calls = []
    monkeypatch.setattr(notify_service, "send_email", lambda c, s, h, t: email_calls.append(s))

    def boom(c, t):
        raise RuntimeError("bad token")

    monkeypatch.setattr(notify_service, "send_telegram", boom)

    result = notify_service.test_config(cfg)

    by_ch = {r.channel: r for r in result.results}
    assert by_ch["email"].ok is True
    assert len(email_calls) == 2  # 成功样例 + 失败样例各一封
    assert by_ch["telegram"].ok is False and "bad token" in by_ch["telegram"].error

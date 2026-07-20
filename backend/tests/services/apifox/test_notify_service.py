"""Apifox 失败通知 · service 集成测试（不触网，monkeypatch 发送）。

覆盖：配置读写(密钥不回传/留空保留)、触发门控(无配置/开关关/渠道错误不影响主流程)。
"""

from app.routers.apifox.notify_schemas import NotifyConfigUpdate
from app.services.apifox import notify_service

PID = 1


def _update(db, **kw):
    base = dict(
        email_enabled=True, smtp_host="smtp.x", smtp_port=465, smtp_username="u",
        email_recipients=["a@x.com"], notify_run=True,
    )
    base.update(kw)
    return notify_service.update_config(db, PID, NotifyConfigUpdate(**base))


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


def test_retry_fields_default_and_round_trip(db):
    _update(db)  # 未传重试字段

    out = notify_service.config_out(notify_service.notify_repo.get_by_project(db, PID))
    assert out.retry_count == 0 and out.retry_interval_sec == 5  # 默认不重试

    _update(db, retry_count=2, retry_interval_sec=15)

    out = notify_service.config_out(notify_service.notify_repo.get_by_project(db, PID))
    assert out.retry_count == 2 and out.retry_interval_sec == 15


# ---------- 触发门控 ----------
def test_notify_failure_noop_without_config(db):
    notify_service.notify_failure(db, 999, "run", "t", "d")  # 无配置，不应抛异常


def test_notify_failure_respects_switch(db, monkeypatch):
    _update(db, notify_run=False)  # 关掉执行通知
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda cfg, s, b: sent.append(1))

    notify_service.notify_failure(db, PID, "run", "执行失败", "detail")

    assert sent == []  # 开关关，不发


def test_notify_failure_sends_when_enabled(db, monkeypatch):
    _update(db, notify_run=True)
    sent = []
    monkeypatch.setattr(notify_service, "send_email", lambda cfg, s, b: sent.append((s, b)))

    notify_service.notify_failure(db, PID, "run", "执行失败：套件A", "3/5 失败")

    assert len(sent) == 1 and "执行失败" in sent[0][0]


def test_notify_failure_channel_error_does_not_raise(db, monkeypatch):
    _update(db, notify_run=True)

    def boom(cfg, s, b):
        raise RuntimeError("SMTP down")

    monkeypatch.setattr(notify_service, "send_email", boom)

    notify_service.notify_failure(db, PID, "run", "t", "d")  # 渠道报错不应冒泡


def test_test_config_reports_channel_errors(db, monkeypatch):
    cfg = _update(db, telegram_enabled=True, telegram_bot_token="t", telegram_chat_ids=["1"])
    monkeypatch.setattr(notify_service, "send_email", lambda c, s, b: None)

    def boom(c, t):
        raise RuntimeError("bad token")

    monkeypatch.setattr(notify_service, "send_telegram", boom)

    result = notify_service.test_config(cfg)

    by_ch = {r.channel: r for r in result.results}
    assert by_ch["email"].ok is True
    assert by_ch["telegram"].ok is False and "bad token" in by_ch["telegram"].error

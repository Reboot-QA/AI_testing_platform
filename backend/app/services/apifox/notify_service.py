"""Apifox 失败通知 · 业务层（配置读写 + 邮件/Telegram 发送 + 失败触发）。

notify_failure 由三类触发点（定时任务/套件·场景执行/AI 生成）调用；每个渠道独立
try/except，**通知失败绝不影响主流程**。密钥仅在更新时提供才覆盖，不回传。
"""

import json
import logging
import smtplib
from email.message import EmailMessage
from typing import List

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.notify_config import ApifoxNotifyConfig
from app.repositories.apifox import notify_repo
from app.routers.apifox.notify_schemas import (
    NotifyChannelResult,
    NotifyConfigOut,
    NotifyConfigUpdate,
    NotifyTestResult,
)

logger = logging.getLogger(__name__)

_SWITCH = {"schedule": "notify_schedule", "run": "notify_run", "aigen": "notify_aigen"}


def _json_list(text) -> List[str]:
    if not text:
        return []
    try:
        return [str(x) for x in json.loads(text) if str(x).strip()]
    except (ValueError, TypeError):
        return []


# ---------- 配置读写 ----------
def config_out(cfg: ApifoxNotifyConfig) -> NotifyConfigOut:
    return NotifyConfigOut(
        email_enabled=cfg.email_enabled,
        smtp_host=cfg.smtp_host,
        smtp_port=cfg.smtp_port,
        smtp_username=cfg.smtp_username,
        mail_from=cfg.mail_from,
        email_recipients=_json_list(cfg.email_recipients),
        smtp_password_set=bool(cfg.smtp_password),
        telegram_enabled=cfg.telegram_enabled,
        telegram_chat_ids=_json_list(cfg.telegram_chat_ids),
        telegram_bot_token_set=bool(cfg.telegram_bot_token),
        notify_schedule=cfg.notify_schedule,
        notify_run=cfg.notify_run,
        notify_aigen=cfg.notify_aigen,
        retry_count=cfg.retry_count,
        retry_interval_sec=cfg.retry_interval_sec,
    )


def update_config(db: Session, project_id: int, data: NotifyConfigUpdate) -> ApifoxNotifyConfig:
    cfg = notify_repo.get_or_create(db, project_id)
    cfg.email_enabled = data.email_enabled
    cfg.smtp_host = data.smtp_host
    cfg.smtp_port = data.smtp_port
    cfg.smtp_username = data.smtp_username
    cfg.mail_from = data.mail_from
    cfg.email_recipients = json.dumps(data.email_recipients, ensure_ascii=False)
    cfg.telegram_enabled = data.telegram_enabled
    cfg.telegram_chat_ids = json.dumps(data.telegram_chat_ids, ensure_ascii=False)
    cfg.notify_schedule = data.notify_schedule
    cfg.notify_run = data.notify_run
    cfg.notify_aigen = data.notify_aigen
    cfg.retry_count = data.retry_count
    cfg.retry_interval_sec = data.retry_interval_sec
    if data.smtp_password:  # 留空=保留原密钥
        cfg.smtp_password = data.smtp_password
    if data.telegram_bot_token:
        cfg.telegram_bot_token = data.telegram_bot_token
    db.commit()
    db.refresh(cfg)
    return cfg


# ---------- 发送 ----------
def send_email(cfg: ApifoxNotifyConfig, subject: str, body: str) -> None:
    recipients = _json_list(cfg.email_recipients)
    if not cfg.smtp_host or not recipients:
        raise ValueError("邮件未配置 SMTP 主机或收件人")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.mail_from or cfg.smtp_username or ""
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)
    port = cfg.smtp_port or 465
    if port == 465:
        with smtplib.SMTP_SSL(cfg.smtp_host, port, timeout=10) as server:
            if cfg.smtp_username:
                server.login(cfg.smtp_username, cfg.smtp_password or "")
            server.send_message(msg)
    else:
        with smtplib.SMTP(cfg.smtp_host, port, timeout=10) as server:
            server.starttls()
            if cfg.smtp_username:
                server.login(cfg.smtp_username, cfg.smtp_password or "")
            server.send_message(msg)


def send_telegram(cfg: ApifoxNotifyConfig, text: str) -> None:
    chat_ids = _json_list(cfg.telegram_chat_ids)
    if not cfg.telegram_bot_token or not chat_ids:
        raise ValueError("Telegram 未配置 Bot Token 或 chat_id")
    with httpx.Client(timeout=10) as client:
        for chat_id in chat_ids:
            resp = client.post(
                f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
            resp.raise_for_status()


# ---------- 失败触发（供三类触发点调用） ----------
def notify_failure(db: Session, project_id: int, event_type: str, title: str, detail: str) -> None:
    cfg = notify_repo.get_by_project(db, project_id)
    if not cfg or not getattr(cfg, _SWITCH.get(event_type, ""), False):
        return
    subject = f"[失败通知] {title}"
    body = f"{title}\n\n{detail}"
    if cfg.email_enabled:
        try:
            send_email(cfg, subject, body)
        except Exception:  # noqa: BLE001 - 通知失败不影响主流程
            logger.exception("失败通知·邮件发送失败 project=%s", project_id)
    if cfg.telegram_enabled:
        try:
            send_telegram(cfg, body)
        except Exception:  # noqa: BLE001 - 通知失败不影响主流程
            logger.exception("失败通知·Telegram 发送失败 project=%s", project_id)


def test_config(cfg: ApifoxNotifyConfig) -> NotifyTestResult:
    """按已启用渠道各发一条测试消息，如实回报每个渠道的结果（成功/错误信息）。"""
    results: List[NotifyChannelResult] = []
    if cfg.email_enabled:
        try:
            send_email(cfg, "[测试] AI 测试平台失败通知", "这是一条通知配置测试消息，收到即表示邮件渠道可用。")
            results.append(NotifyChannelResult(channel="email", ok=True))
        except Exception as exc:  # noqa: BLE001 - 如实回报配置错误
            results.append(NotifyChannelResult(channel="email", ok=False, error=str(exc)[:300]))
    if cfg.telegram_enabled:
        try:
            send_telegram(cfg, "[测试] AI 测试平台失败通知：收到即表示 Telegram 渠道可用。")
            results.append(NotifyChannelResult(channel="telegram", ok=True))
        except Exception as exc:  # noqa: BLE001 - 如实回报配置错误
            results.append(NotifyChannelResult(channel="telegram", ok=False, error=str(exc)[:300]))
    return NotifyTestResult(results=results)

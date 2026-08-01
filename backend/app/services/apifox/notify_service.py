"""Apifox 通知 · 业务层（配置读写 + 邮件/Telegram 发送 + 成功/失败触发）。

notify_event 由四类触发点（定时任务/套件·场景执行/AI 生成/定时导入）调用；成功与
失败各由独立开关控制。每个渠道独立 try/except，**通知失败绝不影响主流程**。
展示交给 notify_templates（成功✅/失败❌两套，邮件 HTML）；密钥仅在更新时提供才覆盖。
"""

import json
import logging
import smtplib
from datetime import datetime
from email.header import Header
from email.message import EmailMessage
from typing import List

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.notify_config import ApifoxNotifyConfig
from app.models.project import Project
from app.repositories.apifox import notify_repo
from app.routers.apifox.notify_schemas import (
    NotifyChannelResult,
    NotifyConfigOut,
    NotifyConfigUpdate,
    NotifyTestResult,
)
from app.services.apifox.notify_templates import (
    NotifyPayload,
    render_email_html,
    render_email_text,
    render_subject,
    render_telegram,
)

logger = logging.getLogger(__name__)

# 事件 → 开关列（成功/失败各一套）。import_schedule 复用定时任务开关（无独立 UI 项）。
_FAIL_SWITCH = {
    "schedule": "notify_schedule",
    "run": "notify_run",
    "aigen": "notify_aigen",
    "import_schedule": "notify_schedule",
}
_SUCCESS_SWITCH = {
    "schedule": "notify_schedule_success",
    "run": "notify_run_success",
    "aigen": "notify_aigen_success",
    "import_schedule": "notify_schedule_success",
}


def project_name(db: Session, project_id: int) -> str:
    """通知里展示的项目名（查不到回退占位，绝不因缺项目而中断通知）。"""
    name = db.query(Project.name).filter(Project.id == project_id).scalar()
    return name or f"项目#{project_id}"


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
        notify_schedule_success=cfg.notify_schedule_success,
        notify_run_success=cfg.notify_run_success,
        notify_aigen_success=cfg.notify_aigen_success,
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
    cfg.notify_schedule_success = data.notify_schedule_success
    cfg.notify_run_success = data.notify_run_success
    cfg.notify_aigen_success = data.notify_aigen_success
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
def send_email(cfg: ApifoxNotifyConfig, subject: str, html: str, text: str) -> None:
    """发 HTML 邮件（带纯文本兜底）。text 必须先 set，html 作为 alternative 追加。"""
    recipients = _json_list(cfg.email_recipients)
    if not cfg.smtp_host or not recipients:
        raise ValueError("邮件未配置 SMTP 主机或收件人")
    msg = EmailMessage()
    msg["Subject"] = str(Header(subject, "utf-8"))
    msg["From"] = cfg.mail_from or cfg.smtp_username or ""
    msg["To"] = ", ".join(recipients)
    msg.set_content(text, charset="utf-8")
    msg.add_alternative(html, subtype="html", charset="utf-8")
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
    """发 Telegram（HTML parse_mode；文本由 notify_templates 渲染并已转义）。"""
    chat_ids = _json_list(cfg.telegram_chat_ids)
    if not cfg.telegram_bot_token or not chat_ids:
        raise ValueError("Telegram 未配置 Bot Token 或 chat_id")
    with httpx.Client(timeout=10) as client:
        for chat_id in chat_ids:
            resp = client.post(
                f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            )
            resp.raise_for_status()


# ---------- 触发（供四类触发点调用） ----------
def _switch_enabled(cfg: ApifoxNotifyConfig, payload: NotifyPayload) -> bool:
    table = _SUCCESS_SWITCH if payload.is_success else _FAIL_SWITCH
    col = table.get(payload.event_type)
    return bool(col) and bool(getattr(cfg, col, False))


def notify_event(db: Session, project_id: int, payload: NotifyPayload) -> None:
    """按项目配置 + 成功/失败开关推送一条通知（成功与失败共用此入口）。"""
    cfg = notify_repo.get_by_project(db, project_id)
    if not cfg or not _switch_enabled(cfg, payload):
        return
    if cfg.email_enabled:
        try:
            send_email(cfg, render_subject(payload), render_email_html(payload), render_email_text(payload))
        except Exception:  # noqa: BLE001 - 通知失败不影响主流程
            logger.exception("通知·邮件发送失败 project=%s event=%s", project_id, payload.event_type)
    if cfg.telegram_enabled:
        try:
            send_telegram(cfg, render_telegram(payload))
        except Exception:  # noqa: BLE001 - 通知失败不影响主流程
            logger.exception("通知·Telegram 发送失败 project=%s event=%s", project_id, payload.event_type)


# ---------- 测试发送 ----------
def _sample_payload(result: str) -> NotifyPayload:
    """测试按钮用的样例载荷：让用户直观看到成功/失败最终样式。"""
    passed, failed = (12, 0) if result == "success" else (9, 3)
    return NotifyPayload(
        event_type="run",
        result=result,
        project_name="示例项目",
        scene="套件执行",
        target_name="登录冒烟" if result == "success" else "支付主流程",
        total=12,
        passed=passed,
        failed=failed,
        duration_ms=3400 if result == "success" else 8100,
        ref_id=1287 if result == "success" else 1288,
        triggered_by="manual",
        happened_at=datetime.now(),
    )


def test_config(cfg: ApifoxNotifyConfig) -> NotifyTestResult:
    """按已启用渠道各发一条成功样例 + 一条失败样例，让用户看到两种样式。"""
    results: List[NotifyChannelResult] = []
    samples = [_sample_payload("success"), _sample_payload("failure")]
    if cfg.email_enabled:
        try:
            for p in samples:
                send_email(cfg, f"[测试] {render_subject(p)}", render_email_html(p), render_email_text(p))
            results.append(NotifyChannelResult(channel="email", ok=True))
        except Exception as exc:  # noqa: BLE001 - 如实回报配置错误
            results.append(NotifyChannelResult(channel="email", ok=False, error=str(exc)[:300]))
    if cfg.telegram_enabled:
        try:
            for p in samples:
                send_telegram(cfg, render_telegram(p))
            results.append(NotifyChannelResult(channel="telegram", ok=True))
        except Exception as exc:  # noqa: BLE001 - 如实回报配置错误
            results.append(NotifyChannelResult(channel="telegram", ok=False, error=str(exc)[:300]))
    return NotifyTestResult(results=results)

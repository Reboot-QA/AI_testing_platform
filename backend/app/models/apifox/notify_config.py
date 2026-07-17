"""Apifox 失败通知 · 项目级配置模型（一对一 project）。

每个项目单独配置邮件/Telegram 渠道 + 固定收件人 + 三类触发开关；该项目的
定时任务/套件·场景执行/AI 生成失败时按配置推送。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxNotifyConfig(Base):
    __tablename__ = "apifox_notify_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # 项目一对一（普通索引列，与项目松耦合，随 project_cleanup 清理）
    project_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    # 邮件（SMTP）
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    smtp_host: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    smtp_port: Mapped[int] = mapped_column(Integer, default=465)
    smtp_username: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    smtp_password: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mail_from: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email_recipients: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 邮箱数组

    # Telegram
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_bot_token: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    telegram_chat_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON chat_id 数组

    # 三类触发开关
    notify_schedule: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    notify_run: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    notify_aigen: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

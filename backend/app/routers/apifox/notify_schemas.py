"""Apifox 失败通知配置 · 请求/响应契约。密钥（SMTP 密码 / Bot Token）不回传，只回是否已设置。"""

from typing import List, Optional

from pydantic import BaseModel, Field


class NotifyConfigOut(BaseModel):
    email_enabled: bool
    smtp_host: Optional[str] = None
    smtp_port: int
    smtp_username: Optional[str] = None
    mail_from: Optional[str] = None
    email_recipients: List[str] = []
    smtp_password_set: bool = False
    telegram_enabled: bool
    telegram_chat_ids: List[str] = []
    telegram_bot_token_set: bool = False
    notify_schedule: bool
    notify_run: bool
    notify_aigen: bool
    # 自动重试（仅定时任务）
    retry_count: int
    retry_interval_sec: int


class NotifyConfigUpdate(BaseModel):
    email_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 465
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None  # 仅在填了新值时更新（留空=保留原密钥）
    mail_from: Optional[str] = None
    email_recipients: List[str] = []
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None  # 仅在填了新值时更新
    telegram_chat_ids: List[str] = []
    notify_schedule: bool = True
    notify_run: bool = True
    notify_aigen: bool = True
    # 自动重试（仅定时任务）：0=不重试；间隔上限 60s，避免长间隔阻塞单线程调度
    retry_count: int = Field(default=0, ge=0, le=5)
    retry_interval_sec: int = Field(default=5, ge=1, le=60)


class NotifyChannelResult(BaseModel):
    channel: str  # email | telegram
    ok: bool
    error: Optional[str] = None


class NotifyTestResult(BaseModel):
    results: List[NotifyChannelResult] = []

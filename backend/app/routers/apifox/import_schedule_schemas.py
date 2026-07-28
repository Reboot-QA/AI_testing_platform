"""Apifox 定时导入 · 请求/响应契约。响应不回传 Basic Auth 密码 / Git Token（仅回布尔标记）。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.constants.limits import TITLE_MAX_LEN


class ImportScheduleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=TITLE_MAX_LEN)
    url: str
    basic_auth_user: Optional[str] = None
    basic_auth_pwd: Optional[str] = None
    git_token: Optional[str] = None
    delete_unreferenced: bool = False
    schedule_type: str = "daily"
    run_time: Optional[str] = "09:00"
    week_day: Optional[int] = None
    interval_minutes: Optional[int] = None
    cron_expr: Optional[str] = None
    enabled: bool = True


class ImportScheduleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=TITLE_MAX_LEN)
    url: Optional[str] = None
    basic_auth_user: Optional[str] = None
    basic_auth_pwd: Optional[str] = None
    git_token: Optional[str] = None
    delete_unreferenced: Optional[bool] = None
    schedule_type: Optional[str] = None
    run_time: Optional[str] = None
    week_day: Optional[int] = None
    interval_minutes: Optional[int] = None
    cron_expr: Optional[str] = None
    enabled: Optional[bool] = None


class ImportScheduleOut(BaseModel):
    id: int
    project_id: int
    name: str
    url: str
    has_basic_auth: bool = False
    has_git_token: bool = False
    delete_unreferenced: bool
    schedule_type: str
    run_time: str
    week_day: Optional[int] = None
    interval_minutes: Optional[int] = None
    cron_expr: Optional[str] = None
    enabled: bool
    schedule_desc: str = ""
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_detail: Optional[str] = None
    next_run_at: Optional[datetime] = None

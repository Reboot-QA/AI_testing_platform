"""Apifox 定时任务 · 请求/响应契约。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScheduleCreate(BaseModel):
    name: str
    target_type: str
    target_id: int
    environment_id: Optional[int] = None
    schedule_type: str = "daily"
    run_time: Optional[str] = "09:00"
    week_day: Optional[int] = None
    interval_minutes: Optional[int] = None
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    environment_id: Optional[int] = None
    schedule_type: Optional[str] = None
    run_time: Optional[str] = None
    week_day: Optional[int] = None
    interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None


class ScheduleOut(BaseModel):
    id: int
    project_id: int
    name: str
    target_type: str
    target_id: int
    target_name: str = ""
    environment_id: Optional[int] = None
    schedule_type: str
    run_time: str
    week_day: Optional[int] = None
    interval_minutes: Optional[int] = None
    enabled: bool
    schedule_desc: str = ""
    last_run_at: Optional[datetime] = None
    last_run_id: Optional[int] = None
    last_run_status: Optional[str] = None
    next_run_at: Optional[datetime] = None

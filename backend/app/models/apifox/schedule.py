"""Apifox 重构 · 定时任务（定时执行用例/场景）。

复用旧调度线程（schedule_service 的轮询范式）；字段与旧 ApiScheduledTask 对齐：
schedule_type ∈ {daily, weekly, interval} + run_time/week_day/interval_minutes。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxSchedule(Base):
    __tablename__ = "apifox_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # case | scenario | suite
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(Integer)
    environment_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # daily | weekly | interval | cron
    schedule_type: Mapped[str] = mapped_column(String(20), default="daily")
    run_time: Mapped[str] = mapped_column(String(5), default="09:00")
    week_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cron_expr: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # schedule_type=cron
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_run_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

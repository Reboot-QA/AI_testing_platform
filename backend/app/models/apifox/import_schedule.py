"""Apifox 重构 · 定时导入任务。

定时从 URL 拉取 OpenAPI/Swagger 等并「更新同步」到项目。调度字段与 ApifoxSchedule 对齐
（duck-typed 复用 schedule_calc / schedule_service 的下次运行计算与校验）；执行体独立
（走 import_sync_service.apply_sync，而非 run_service）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxImportSchedule(Base):
    __tablename__ = "apifox_import_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(1000))
    basic_auth_user: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    basic_auth_pwd: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    git_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # 同步时是否删除「新文档已移除且无用例引用」的接口
    delete_unreferenced: Mapped[bool] = mapped_column(Boolean, default=False)
    # daily | weekly | interval | cron（与 ApifoxSchedule 一致）
    schedule_type: Mapped[str] = mapped_column(String(20), default="daily")
    run_time: Mapped[str] = mapped_column(String(5), default="09:00")
    week_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cron_expr: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_run_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    last_run_detail: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # 上次运行逐条清单 JSON（{items,truncated,...}），供「上次结果」明细表展示；仅存最近一次
    last_run_manifest: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

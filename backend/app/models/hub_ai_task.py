"""平台 AI 任务（需求解析 / 功能用例生成）执行记录，与 apifox 接口 AI 任务并列。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

HUB_AI_TASK_TYPES = ("requirement", "functional")
HUB_AI_TASK_STATUSES = ("pending", "running", "succeeded", "partial", "failed", "canceled")


class HubAiTask(Base):
    __tablename__ = "hub_ai_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    task_type: Mapped[str] = mapped_column(String(20), index=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    target: Mapped[str] = mapped_column(String(500), default="")
    category_label: Mapped[str] = mapped_column(String(200), default="")
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    done_items: Mapped[int] = mapped_column(Integer, default=0)
    generated_total: Mapped[int] = mapped_column(Integer, default=0)
    applied_total: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    progress_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# 无心跳超过该时长仍 running 的任务，列表/详情查询前标记为失败（进程重启、SSE 中断等）
HUB_AI_TASK_STALE_MINUTES = 10
# 无后台 worker 标记且长时间无更新的 running，视为僵尸任务（假 running）
HUB_AI_TASK_ORPHAN_MINUTES = 3

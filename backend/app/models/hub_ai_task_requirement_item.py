"""AI 需求解析任务产出的需求点草稿（供任务详情查看与后续入库）。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HubAiTaskRequirementItem(Base):
    __tablename__ = "hub_ai_task_requirement_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    req_type: Mapped[str] = mapped_column(String(50), default="functional")
    priority: Mapped[str] = mapped_column(String(20), default="P1")
    requirement_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    imported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

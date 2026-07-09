"""Apifox 重构 · 项目级全局参数（执行时自动附加到请求，附加逻辑留 P4）。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxGlobalParam(Base):
    __tablename__ = "apifox_global_params"
    __table_args__ = (
        UniqueConstraint("project_id", "location", "key", name="uq_apifox_gparam_project_loc_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    # header | query | cookie | body
    location: Mapped[str] = mapped_column(String(20), default="header")
    key: Mapped[str] = mapped_column(String(200))
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

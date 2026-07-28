"""Apifox 重构 · 项目级 API Token。

供「通过 API 导入/导出」用：外部系统带 X-API-Token 头调用，无需 JWT。Token 明文存储
（仅项目内可见、可随时吊销），project 作用域，鉴权即锁定项目，不跨项目。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxApiToken(Base):
    __tablename__ = "apifox_api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    token: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

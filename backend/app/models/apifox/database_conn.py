"""Apifox 重构 · 环境级数据库连接（供场景「数据库操作」步骤造数/清理/取数）。

挂在环境下（dev 环境连 dev 库、prod 连 prod 库，与 base_url 同级）。密码明文存储
（与环境变量 remote_value 一致，非本次新增风险）。当前仅 MySQL。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxEnvironmentDatabase(Base):
    __tablename__ = "apifox_environment_databases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    environment_id: Mapped[int] = mapped_column(
        ForeignKey("apifox_environments.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    # 当前仅 mysql（后续可扩 postgresql）
    db_type: Mapped[str] = mapped_column(String(20), default="mysql")
    host: Mapped[str] = mapped_column(String(200), default="")
    port: Mapped[int] = mapped_column(Integer, default=3306)
    username: Mapped[str] = mapped_column(String(100), default="")
    password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    database: Mapped[str] = mapped_column(String(200), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

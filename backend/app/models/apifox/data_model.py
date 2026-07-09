"""Apifox 重构 · 数据模型（可复用 JSON Schema）。

项目级复用结构（如「用户对象」「分页响应」）；接口/用例引用与契约校验留 P4（届时带迁移）。
json_schema 存原始 JSON 文本，保存时仅校验合法 JSON。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxSchema(Base):
    __tablename__ = "apifox_schemas"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_apifox_schema_project_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    json_schema: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

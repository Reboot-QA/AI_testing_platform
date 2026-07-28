"""Apifox 重构 · 项目级 SQL 脚本库（引用式，对齐 apifox_scripts）。

SQL 跟随项目走（可复用资源）；前后置处理器通过 processor JSON 里 kind=database_script 的
sql_script_id 引用（非关联表），执行时读库最新 SQL。有引用禁删、名唯一、乐观锁 version。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxSqlScript(Base):
    __tablename__ = "apifox_sql_scripts"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_apifox_sql_script_project_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # 乐观锁版本：每次保存 +1，多人并发编辑冲突检测
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

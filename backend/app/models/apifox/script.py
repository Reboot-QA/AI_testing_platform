"""Apifox 重构 · 项目级脚本库 + 用例前后置引用。

脚本跟随项目走（可复用资源）；用例前后置通过 apifox_case_scripts 引用库脚本（phase pre|post）。
脚本执行留 P4。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxScript(Base):
    __tablename__ = "apifox_scripts"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_apifox_script_project_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # javascript | python
    lang: Mapped[str] = mapped_column(String(20), default="javascript")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # 乐观锁版本：每次保存 +1，多人并发编辑冲突检测
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxCaseScript(Base):
    __tablename__ = "apifox_case_scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("apifox_endpoint_cases.id"), index=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("apifox_scripts.id"), index=True)
    # pre | post
    phase: Mapped[str] = mapped_column(String(10))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ApifoxEndpointScript(Base):
    """接口级前后置脚本引用（镜像 ApifoxCaseScript，挂 endpoint）。"""

    __tablename__ = "apifox_endpoint_scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("apifox_endpoints.id"), index=True)
    script_id: Mapped[int] = mapped_column(ForeignKey("apifox_scripts.id"), index=True)
    # pre | post
    phase: Mapped[str] = mapped_column(String(10))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

"""Apifox 重构 · 接口管理规范化模型（文件夹树 + 接口 Endpoint）。

request_spec 存结构化 JSON（请求「数据」：query/path_params/headers/body/auth），
断言/提取/脚本等「行为」不在此，留给后续接口用例/场景层——即拆 __meta blob 的落点。
全部 project 作用域，访问控制走 project_access_service（部门+owner+admin）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxFolder(Base):
    __tablename__ = "apifox_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_folders.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxEndpoint(Base):
    __tablename__ = "apifox_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    folder_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_folders.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(String(10), default="GET")
    path: Mapped[str] = mapped_column(String(500))
    # 结构化 JSON：query/path_params/headers/body/auth
    request_spec: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

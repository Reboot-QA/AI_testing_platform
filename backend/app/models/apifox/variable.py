"""Apifox 重构 · 环境与变量规范化模型（行级 + 远程/本地）。

变量行级化（每变量一行，修 blob 整列覆盖丢更新）；远程值=团队共享，本地值=按用户覆盖。
全部 project 作用域；与旧 api_environments/blob 灰度并存，执行时对接留 P4。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApifoxEnvironment(Base):
    __tablename__ = "apifox_environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    # 命名前置 URL（base_url 为默认前置 URL）
    servers: Mapped[list["ApifoxEnvironmentServer"]] = relationship(
        "ApifoxEnvironmentServer",
        cascade="all, delete-orphan",
        order_by="ApifoxEnvironmentServer.sort_order",
    )


class ApifoxEnvironmentServer(Base):
    """环境的命名前置 URL（如「服务A → https://a.xxx」）。接口按 server_name 跨环境匹配同名。"""

    __tablename__ = "apifox_environment_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    environment_id: Mapped[int] = mapped_column(
        ForeignKey("apifox_environments.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxEnvironmentVariable(Base):
    __tablename__ = "apifox_environment_variables"
    __table_args__ = (
        UniqueConstraint("environment_id", "key", name="uq_apifox_env_var_env_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    environment_id: Mapped[int] = mapped_column(
        ForeignKey("apifox_environments.id"), index=True
    )
    key: Mapped[str] = mapped_column(String(200))
    remote_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxEnvironmentVarLocal(Base):
    __tablename__ = "apifox_environment_var_locals"
    __table_args__ = (
        UniqueConstraint(
            "environment_variable_id", "user_id", name="uq_apifox_env_var_local_var_user"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    environment_variable_id: Mapped[int] = mapped_column(
        ForeignKey("apifox_environment_variables.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    local_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxGlobalVariable(Base):
    __tablename__ = "apifox_global_variables"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_apifox_global_var_project_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    key: Mapped[str] = mapped_column(String(200))
    remote_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxGlobalVarLocal(Base):
    __tablename__ = "apifox_global_var_locals"
    __table_args__ = (
        UniqueConstraint(
            "global_variable_id", "user_id", name="uq_apifox_global_var_local_var_user"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    global_variable_id: Mapped[int] = mapped_column(
        ForeignKey("apifox_global_variables.id"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    local_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

"""Apifox 重构 · 接口管理规范化模型（文件夹树 + 接口 Endpoint）。

request_spec 存结构化 JSON（请求「数据」：query/path_params/headers/body/auth），
断言/提取/脚本等「行为」不在此，留给后续接口用例/场景层——即拆 __meta blob 的落点。
全部 project 作用域，访问控制走 project_access_service（部门+owner+admin）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxFolder(Base):
    __tablename__ = "apifox_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_folders.id"), nullable=True, index=True
    )
    # endpoint | scenario —— 同一张表按 kind 区分接口文件夹与场景文件夹
    kind: Mapped[str] = mapped_column(String(20), default="endpoint", server_default="endpoint", index=True)
    name: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxEndpointAssertion(Base):
    """接口级断言（镜像 ApifoxCaseAssertion，挂 endpoint）。运行/调试时与用例断言合并叠加。"""

    __tablename__ = "apifox_endpoint_assertions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("apifox_endpoints.id"), index=True)
    # status_code | json_path | header | contains | response_time
    type: Mapped[str] = mapped_column(String(20))
    path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    operator: Mapped[str] = mapped_column(String(20), default="eq")
    expected: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ApifoxEndpointExtract(Base):
    """接口级提取（镜像 ApifoxCaseExtract，挂 endpoint）。"""

    __tablename__ = "apifox_endpoint_extracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("apifox_endpoints.id"), index=True)
    var_name: Mapped[str] = mapped_column(String(200))
    # response_json | response_header | response_text | ...
    source: Mapped[str] = mapped_column(String(30), default="response_json")
    path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # temporary | environment | global
    scope: Mapped[str] = mapped_column(String(20), default="temporary")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


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
    # 选用的命名前置 URL 名（空=用环境默认前置 URL base_url）
    server_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 结构化 JSON：query/path_params/headers/body/auth
    request_spec: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 响应契约：绑定的数据模型 id（空=不校验）+ 契约不符是否判失败
    response_schema_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_schemas.id"), nullable=True
    )
    contract_strict: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # 乐观锁版本：每次保存 +1，多人并发编辑冲突检测（多 tab 同开同一接口）
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

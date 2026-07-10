"""Apifox 重构 · 接口用例（单接口用例）模型。

用例引用一个 Endpoint；断言/提取拆行表（可查询/可报表，拆 __meta 行为的核心）；
请求/用例变量/数据驱动走结构化 JSON 列。脚本不在此（走后续项目级脚本库）。执行消费留 P4。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxEndpointCase(Base):
    __tablename__ = "apifox_endpoint_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("apifox_endpoints.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    # 结构化 JSON：request_spec(query/path/headers/body/auth)、用例变量、数据驱动
    request_spec: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data_drive: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxCaseAssertion(Base):
    __tablename__ = "apifox_case_assertions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("apifox_endpoint_cases.id"), index=True)
    # status_code | json_path | header | contains | response_time
    type: Mapped[str] = mapped_column(String(20))
    path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # eq|neq|contains|not_contains|gt|gte|lt|lte|regex|exists（仅 status_code/json_path/header 用）
    operator: Mapped[str] = mapped_column(String(20), default="eq")
    expected: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ApifoxCaseExtract(Base):
    __tablename__ = "apifox_case_extracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("apifox_endpoint_cases.id"), index=True)
    var_name: Mapped[str] = mapped_column(String(200))
    # response_json | response_header | response_text | ...
    source: Mapped[str] = mapped_column(String(30), default="response_json")
    path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # temporary | environment | global
    scope: Mapped[str] = mapped_column(String(20), default="temporary")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

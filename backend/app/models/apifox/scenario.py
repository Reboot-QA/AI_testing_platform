"""Apifox 重构 · 场景编排模型（业务链路 = 有序步骤：用例引用/等待/子场景）。

步骤引用接口用例（用例自带请求/断言/提取/前后置脚本）；子场景复用需防循环（service 校验）。
执行（跑场景/变量流转）留 P4。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxScenario(Base):
    __tablename__ = "apifox_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxScenarioStep(Base):
    __tablename__ = "apifox_scenario_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("apifox_scenarios.id"), index=True)
    # 控制步骤(group/if/loop)嵌套父步骤；顶层步骤为 NULL
    parent_step_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_scenario_steps.id"), nullable=True, index=True
    )
    # case | wait | scenario | group（后续片加 if | loop）
    type: Mapped[str] = mapped_column(String(20))
    ref_case_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_endpoint_cases.id"), nullable=True, index=True
    )
    ref_scenario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_scenarios.id"), nullable=True, index=True
    )
    wait_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 控制步骤配置 JSON（分组无配置；条件/循环后续片用）
    config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 步骤备注（可选）
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

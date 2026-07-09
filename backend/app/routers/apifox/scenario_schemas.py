"""Apifox 场景编排 · 请求/响应契约。

步骤类型：case(引用接口用例) | wait(等待毫秒) | scenario(子场景，防循环)。
StepOut 带展示字段（用例名/接口方法路径/子场景名），执行留 P4。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StepIn(BaseModel):
    type: str  # case | wait | scenario
    ref_case_id: Optional[int] = None
    ref_scenario_id: Optional[int] = None
    wait_ms: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=200)
    enabled: bool = True


class StepOut(StepIn):
    # 展示字段（服务端填充）
    case_name: str = ""
    endpoint_method: str = ""
    endpoint_path: str = ""
    scenario_name: str = ""


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    steps: List[StepIn] = Field(default_factory=list)


class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    steps: Optional[List[StepIn]] = None
    sort_order: Optional[int] = None


class ScenarioBrief(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    step_count: int = 0
    sort_order: int


class ScenarioOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    steps: List[StepOut]
    sort_order: int
    created_at: datetime
    updated_at: datetime

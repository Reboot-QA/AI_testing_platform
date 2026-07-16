"""Apifox 场景编排 · 请求/响应契约。

步骤类型：case(引用接口用例) | wait(等待毫秒) | scenario(子场景，防循环) | group(分组容器)。
控制步骤(group 等)用 children 承载嵌套子步骤，config 承载控制参数。
StepOut 带展示字段（用例名/接口方法路径/子场景名）。
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ScenarioPriority = Literal["high", "medium", "low"]


class StepIn(BaseModel):
    type: str  # case | wait | scenario | group
    ref_case_id: Optional[int] = None
    ref_scenario_id: Optional[int] = None
    wait_ms: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    name: Optional[str] = Field(default=None, max_length=200)
    enabled: bool = True
    children: List["StepIn"] = Field(default_factory=list)


class StepOut(StepIn):
    # 展示字段（服务端填充）
    case_name: str = ""
    endpoint_method: str = ""
    endpoint_path: str = ""
    scenario_name: str = ""
    # 输出侧递归收窄为 StepOut，保证嵌套子步骤保留展示字段（List 不变型，故 ignore 覆写告警）
    children: List["StepOut"] = Field(default_factory=list)  # type: ignore[assignment]


class ScenarioRunConfig(BaseModel):
    # 整场景循环次数（绑数据集时以数据集行数为准，此值忽略）；1000 硬上限防误配爆量
    loop_count: int = Field(default=1, ge=1, le=1000)
    # 绑定的项目数据集 id：设置后按数据集每行数据驱动整条场景各跑一遍
    dataset_id: Optional[int] = None
    # 登录态跨步骤透传：共享 cookie jar + 自动捕获/注入 token；默认开（登录/refresh 免手动提取）
    propagate_auth: bool = True


class ScenarioFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ScenarioFolderUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class ScenarioFolderOut(BaseModel):
    id: int
    name: str
    scenario_count: int = 0


class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    priority: ScenarioPriority = "medium"
    folder_id: Optional[int] = None
    steps: List[StepIn] = Field(default_factory=list)


class ScenarioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    priority: Optional[ScenarioPriority] = None
    folder_id: Optional[int] = None
    steps: Optional[List[StepIn]] = None
    sort_order: Optional[int] = None
    run_config: Optional[ScenarioRunConfig] = None
    # 乐观锁：客户端读取时的版本；服务端不一致则 409（None=不校验，向后兼容）
    expected_version: Optional[int] = None


class ScenarioBrief(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    priority: ScenarioPriority = "medium"
    folder_id: Optional[int] = None
    step_count: int = 0
    sort_order: int


class ScenarioOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    priority: ScenarioPriority = "medium"
    folder_id: Optional[int] = None
    steps: List[StepOut]
    sort_order: int
    run_config: ScenarioRunConfig = Field(default_factory=ScenarioRunConfig)
    version: int = 1
    created_at: datetime
    updated_at: datetime


StepIn.model_rebuild()
StepOut.model_rebuild()

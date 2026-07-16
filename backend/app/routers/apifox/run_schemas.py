"""Apifox 运行记录 · 响应契约（SSE 事件为原始 dict 流，不在此定义）。"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunBrief(BaseModel):
    id: int
    parent_run_id: Optional[int] = None
    target_type: str
    target_id: int
    target_name: str
    environment_id: Optional[int] = None
    status: str
    total_count: int
    passed_count: int
    failed_count: int
    pass_rate: Optional[float] = None
    duration_ms: Optional[float] = None
    triggered_by: str
    started_at: datetime
    finished_at: Optional[datetime] = None


class RunStepOut(BaseModel):
    id: int
    step_type: str
    depth: int = 0
    iteration: int = 0
    case_id: Optional[int] = None
    case_name: str
    method: str
    url: str
    status: str
    duration_ms: Optional[float] = None
    response_status: Optional[int] = None
    request_headers: Dict[str, Any] = Field(default_factory=dict)
    request_body: str = ""
    response_headers: Dict[str, Any] = Field(default_factory=dict)
    response_body: str = ""
    assertion_results: List[Dict[str, Any]] = Field(default_factory=list)
    extract_results: List[Dict[str, Any]] = Field(default_factory=list)
    script_logs: List[str] = Field(default_factory=list)
    contract_result: Optional[Dict[str, Any]] = None
    warnings: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class RunOut(RunBrief):
    steps: List[RunStepOut] = Field(default_factory=list)
    # 套件父运行的子运行汇总（各用例/场景一条）；非套件运行为空
    children: List[RunBrief] = Field(default_factory=list)
    # 数据驱动/循环多轮的每组注入数据（[{...}, ...]）；单轮运行为空=报告不分组
    iterations: List[Dict[str, Any]] = Field(default_factory=list)

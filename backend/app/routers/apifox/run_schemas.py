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
    # 定时任务失败重试链：retry_of_run_id 指向链头 run（首次为 None），attempt 为第几次尝试(1 基)
    retry_of_run_id: Optional[int] = None
    attempt: int = 1
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None


class RunBriefWithRetries(RunBrief):
    """报告列表行：同一次触发的多次尝试折成一行。

    本行 = 最后一次尝试（整体结果），retries = 此前各次尝试（attempt 升序）；无重试时为空。
    分页与总条数按「行」（重试链）计，不按尝试次数计。
    """

    retries: List[RunBrief] = Field(default_factory=list)


class RunPageOut(BaseModel):
    items: List[RunBriefWithRetries]
    total: int
    page: int
    page_size: int


class RunBatchDeleteIn(BaseModel):
    run_ids: List[int]


class RunBatchDeleteOut(BaseModel):
    succeeded: int
    failed: int
    errors: List[str] = Field(default_factory=list)


class RunStepOut(BaseModel):
    id: int
    step_type: str
    depth: int = 0
    iteration: int = 0
    loop_round: int = 0
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

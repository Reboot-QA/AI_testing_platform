"""Apifox 运行记录 · 响应契约（SSE 事件为原始 dict 流，不在此定义）。"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RunBrief(BaseModel):
    id: int
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
    error_message: Optional[str] = None


class RunOut(RunBrief):
    steps: List[RunStepOut] = Field(default_factory=list)

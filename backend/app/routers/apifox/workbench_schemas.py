"""Apifox 工作台 · 响应契约（跨项目聚合概览）。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class WorkbenchStats(BaseModel):
    project_count: int
    endpoint_count: int
    scenario_count: int
    running_count: int
    today_pass_rate: Optional[float] = None  # 0-100；当日无已结束 run 时为 None


class WorkbenchProject(BaseModel):
    id: int
    name: str
    endpoint_count: int
    scenario_count: int
    case_count: int
    role: str  # 管理员 / 负责人 / 成员（派生自全局角色与 owner，无项目内角色）


class WorkbenchRunning(BaseModel):
    run_id: int
    project_id: int
    project_name: str
    target_type: str
    target_name: str
    environment_name: Optional[str] = None
    started_at: datetime


class WorkbenchReport(BaseModel):
    run_id: int
    project_id: int
    project_name: str
    target_name: str
    environment_name: Optional[str] = None
    status: str
    passed_count: int
    total_count: int
    pass_rate: Optional[float] = None
    started_at: datetime


class WorkbenchOverviewOut(BaseModel):
    stats: WorkbenchStats
    projects: List[WorkbenchProject]
    running: List[WorkbenchRunning]
    recent_reports: List[WorkbenchReport]

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
    owner_seq: int = 0
    name: str
    description: Optional[str] = None
    endpoint_count: int
    scenario_count: int
    case_count: int
    role: str  # 管理员 / 负责人 / 成员（派生自全局角色与 owner，无项目内角色）
    owner_name: str = ""  # 负责人（owner）用户名 + 真实姓名，供列表按负责人搜索
    department_name: str = ""  # 创建人所属部门（项目 department_id）
    pinned: bool = False  # 当前用户是否置顶


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
    target_type: str
    target_name: str
    environment_name: Optional[str] = None
    status: str
    passed_count: int
    total_count: int
    pass_rate: Optional[float] = None
    started_at: datetime
    error_message: Optional[str] = None  # 失败时取首个失败步骤原因；非失败为 None


class WorkbenchRunningPageOut(BaseModel):
    items: List[WorkbenchRunning]
    total: int
    page: int
    page_size: int


class WorkbenchReportPageOut(BaseModel):
    items: List[WorkbenchReport]
    total: int
    page: int
    page_size: int


class WorkbenchSchedule(BaseModel):
    schedule_id: int
    project_id: int
    project_name: str
    name: str
    target_type: str
    schedule_type: str
    next_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None


class WorkbenchManual(BaseModel):
    run_id: int
    project_id: int
    project_name: str
    name: str
    status: str  # waiting | running | finished
    passed_count: int
    failed_count: int
    total_count: int
    created_at: datetime


class WorkbenchSchedulePageOut(BaseModel):
    items: List[WorkbenchSchedule]
    total: int
    page: int
    page_size: int


class WorkbenchManualPageOut(BaseModel):
    items: List[WorkbenchManual]
    total: int
    page: int
    page_size: int


class WorkbenchAiTask(BaseModel):
    """跨项目 AI 任务（Hub 需求/用例 + Apifox 接口生成）。"""

    task_key: str  # hub:{id} | endpoint:{id}
    category: str  # requirement | functional | endpoint
    task_id: int
    project_id: int
    project_name: str
    title: str
    status: str
    done_items: int = 0
    total_items: int = 0
    updated_at: datetime


class WorkbenchAiTaskPageOut(BaseModel):
    items: List[WorkbenchAiTask]
    total: int
    page: int
    page_size: int


class WorkbenchOverviewOut(BaseModel):
    stats: WorkbenchStats
    projects: List[WorkbenchProject]


class DailyTrendItem(BaseModel):
    date: str  # "2026-07-16"
    passed: int
    failed: int
    total: int
    pass_rate: Optional[float] = None  # 0-100；当日无已结束 run 时为 None


class ProjectStatsOut(BaseModel):
    endpoint_count: int
    case_count: int
    scenario_count: int
    suite_count: int
    running_count: int
    today_pass_rate: Optional[float] = None
    trend: List[DailyTrendItem]  # 最近 7 天（含今天，按日升序）

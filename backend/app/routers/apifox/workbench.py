"""Apifox 工作台 · 路由（跨项目只读聚合概览，作用域=当前用户可见项目）。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.routers.apifox.workbench_schemas import (
    ProjectStatsOut,
    WorkbenchAiTaskPageOut,
    WorkbenchManualPageOut,
    WorkbenchOverviewOut,
    WorkbenchReportPageOut,
    WorkbenchRunningPageOut,
    WorkbenchSchedulePageOut,
)
from app.services.apifox import workbench_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·工作台"])


@router.get("/projects/{project_id}/stats", response_model=ProjectStatsOut)
def project_stats(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, project_id, user)
    return workbench_service.get_project_stats(db, project_id)


@router.get("/workbench/overview", response_model=WorkbenchOverviewOut)
def workbench_overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return workbench_service.get_overview(db, user)


@router.get("/workbench/running", response_model=WorkbenchRunningPageOut)
def workbench_running(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return workbench_service.list_running_page(db, user, page, page_size)


@router.get("/workbench/reports", response_model=WorkbenchReportPageOut)
def workbench_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    status: str | None = Query(None, description="按运行状态筛选：running/passed/failed"),
    target_type: str | None = Query(None, description="按目标类型筛选：case/scenario/suite"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return workbench_service.list_reports_page(db, user, page, page_size, status, target_type)


@router.get("/workbench/failures", response_model=WorkbenchReportPageOut)
def workbench_failures(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """失败聚焦：跨项目最近失败运行 + 失败原因（复用报告响应形状，error_message 已填充）。"""
    return workbench_service.list_failures_page(db, user, page, page_size)


@router.get("/workbench/schedules", response_model=WorkbenchSchedulePageOut)
def workbench_schedules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """即将执行的定时任务（跨项目，启用且有下次执行时间，按 next_run_at 升序）。"""
    return workbench_service.list_schedules_page(db, user, page, page_size)


@router.get("/workbench/manual", response_model=WorkbenchManualPageOut)
def workbench_manual(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手工测试单（跨项目，最近在前）。"""
    return workbench_service.list_manual_page(db, user, page, page_size)


@router.get("/workbench/ai-tasks", response_model=WorkbenchAiTaskPageOut)
def workbench_ai_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 任务（跨项目 Hub 需求/用例 + 接口 AI 生成，按更新时间倒序）。"""
    return workbench_service.list_ai_tasks_page(db, user, page, page_size)

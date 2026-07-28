"""Apifox 定时任务 · 路由（项目作用域 CRUD + 立即执行）。

router 仅参数校验与编排；增删改后一律 refresh_schedule(force_from_now=True) 写 next_run_at。
"""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.schedule import ApifoxSchedule
from app.models.user import User
from app.repositories.apifox import (
    case_repo,
    scenario_repo,
    schedule_repo,
    suite_repo,
    variable_repo,
)
from app.routers.apifox.schedule_schemas import ScheduleCreate, ScheduleOut, ScheduleUpdate
from app.services.apifox import schedule_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·定时任务"])


def _resolve_target(db: Session, project_id: int, target_type: str, target_id: int) -> str:
    """校验目标类型/存在/归属，返回目标名称。"""
    if target_type not in schedule_service.TARGET_TYPES:
        raise ValueError("目标类型无效，支持 case / scenario / suite")
    target: Any
    if target_type == "case":
        target = case_repo.get_case(db, target_id)
    elif target_type == "scenario":
        target = scenario_repo.get_scenario(db, target_id)
    else:
        target = suite_repo.get_suite(db, target_id)
    if not target or target.project_id != project_id:
        raise ValueError("目标用例/场景/套件不存在或不属于该项目")
    return target.name


def _validate_environment(db: Session, project_id: int, environment_id: int | None) -> None:
    if not environment_id:
        return
    env = variable_repo.get_environment(db, environment_id)
    if not env or env.project_id != project_id:
        raise ValueError("环境不存在或不属于该项目")


def _owned_schedule(db: Session, sid: int, user: User) -> ApifoxSchedule:
    task = schedule_repo.get_schedule(db, sid)
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    get_accessible_project(db, task.project_id, user)
    return task


def _clear_irrelevant_schedule_fields(task: ApifoxSchedule) -> None:
    """按当前 schedule_type 清空其它类型专属字段，避免切换后残留僵尸值。"""
    if task.schedule_type != "weekly":
        task.week_day = None
    if task.schedule_type != "interval":
        task.interval_minutes = None
    if task.schedule_type != "cron":
        task.cron_expr = None


def _out(db: Session, task: ApifoxSchedule) -> ScheduleOut:
    target_name = schedule_service.resolve_target_name(db, task.target_type, task.target_id) or ""
    return ScheduleOut(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        target_type=task.target_type,
        target_id=task.target_id,
        target_name=target_name,
        environment_id=task.environment_id,
        schedule_type=task.schedule_type,
        run_time=task.run_time,
        week_day=task.week_day,
        interval_minutes=task.interval_minutes,
        cron_expr=task.cron_expr,
        enabled=task.enabled,
        schedule_desc=schedule_service.describe(task),
        last_run_at=task.last_run_at,
        last_run_id=task.last_run_id,
        last_run_status=task.last_run_status,
        next_run_at=task.next_run_at,
    )


@router.get("/projects/{pid}/schedules", response_model=List[ScheduleOut])
def list_schedules(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return [_out(db, t) for t in schedule_repo.list_schedules(db, pid)]


@router.post("/projects/{pid}/schedules", response_model=ScheduleOut)
def create_schedule(
    pid: int,
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    try:
        _resolve_target(db, pid, data.target_type, data.target_id)
        _validate_environment(db, pid, data.environment_id)
        schedule_service.validate_fields(
            schedule_type=data.schedule_type,
            run_time=data.run_time,
            week_day=data.week_day,
            interval_minutes=data.interval_minutes,
            cron_expr=data.cron_expr,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    task = ApifoxSchedule(
        project_id=pid,
        name=data.name,
        target_type=data.target_type,
        target_id=data.target_id,
        environment_id=data.environment_id,
        schedule_type=data.schedule_type,
        run_time=data.run_time or "09:00",
        week_day=data.week_day,
        interval_minutes=data.interval_minutes,
        cron_expr=data.cron_expr,
        enabled=data.enabled,
    )
    _clear_irrelevant_schedule_fields(task)
    schedule_repo.add(db, task)
    schedule_service.refresh_schedule(db, task, force_from_now=True)
    return _out(db, task)


@router.put("/schedules/{sid}", response_model=ScheduleOut)
def update_schedule(
    sid: int,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = _owned_schedule(db, sid, user)
    payload = data.model_dump(exclude_unset=True)

    target_type = payload.get("target_type", task.target_type)
    target_id = payload.get("target_id", task.target_id)
    schedule_type = payload.get("schedule_type", task.schedule_type)
    try:
        if "target_type" in payload or "target_id" in payload:
            _resolve_target(db, task.project_id, target_type, target_id)
        if "environment_id" in payload:
            _validate_environment(db, task.project_id, payload["environment_id"])
        schedule_service.validate_fields(
            schedule_type=schedule_type,
            run_time=payload.get("run_time", task.run_time),
            week_day=payload.get("week_day", task.week_day),
            interval_minutes=payload.get("interval_minutes", task.interval_minutes),
            cron_expr=payload.get("cron_expr", task.cron_expr),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    for field, value in payload.items():
        setattr(task, field, value)
    _clear_irrelevant_schedule_fields(task)  # 切换调度类型后清理不相关字段，避免僵尸值
    schedule_service.refresh_schedule(db, task, force_from_now=True)
    return _out(db, task)


@router.delete("/schedules/{sid}")
def delete_schedule(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _owned_schedule(db, sid, user)
    schedule_repo.delete(db, task)
    db.commit()
    return {"detail": "已删除"}


@router.post("/schedules/{sid}/run-now", response_model=ScheduleOut)
def run_schedule_now(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _owned_schedule(db, sid, user)
    schedule_service.execute_schedule(db, task)
    db.refresh(task)
    return _out(db, task)

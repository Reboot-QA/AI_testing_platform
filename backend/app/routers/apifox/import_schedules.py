"""Apifox 定时导入 · 路由（项目作用域 CRUD + 立即执行）。

router 仅参数校验与编排；增删改后一律 refresh_schedule(force_from_now=True) 写 next_run_at。
密码 / Token 仅在提供时写入（update 不传即保留原值），响应不回传其明文。
"""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.import_schedule import ApifoxImportSchedule
from app.models.user import User
from app.repositories.apifox import import_schedule_repo
from app.routers.apifox.import_schedule_schemas import (
    ImportRunManifest,
    ImportScheduleCreate,
    ImportScheduleOut,
    ImportScheduleUpdate,
)
from app.services.apifox import import_schedule_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·定时导入"])

# update 时这些字段为空/未传视为「不改」，避免清空已存的凭据
_SECRET_FIELDS = ("basic_auth_pwd", "git_token")


def _owned(db: Session, sid: int, user: User) -> ApifoxImportSchedule:
    task = import_schedule_repo.get_schedule(db, sid)
    if not task:
        raise HTTPException(status_code=404, detail="定时导入任务不存在")
    get_accessible_project(db, task.project_id, user)
    return task


def _clear_irrelevant(task: ApifoxImportSchedule) -> None:
    if task.schedule_type != "weekly":
        task.week_day = None
    if task.schedule_type != "interval":
        task.interval_minutes = None
    if task.schedule_type != "cron":
        task.cron_expr = None


def _parse_manifest(raw: str | None) -> ImportRunManifest | None:
    if not raw:
        return None
    try:
        return ImportRunManifest.model_validate(json.loads(raw))
    except (ValueError, TypeError):
        return None


def _out(db: Session, task: ApifoxImportSchedule) -> ImportScheduleOut:
    return ImportScheduleOut(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        url=task.url,
        has_basic_auth=bool(task.basic_auth_user),
        has_git_token=bool(task.git_token),
        delete_unreferenced=task.delete_unreferenced,
        schedule_type=task.schedule_type,
        run_time=task.run_time,
        week_day=task.week_day,
        interval_minutes=task.interval_minutes,
        cron_expr=task.cron_expr,
        enabled=task.enabled,
        schedule_desc=import_schedule_service.describe(task),
        last_run_at=task.last_run_at,
        last_run_status=task.last_run_status,
        last_run_detail=task.last_run_detail,
        last_run_manifest=_parse_manifest(task.last_run_manifest),
        next_run_at=task.next_run_at,
    )


@router.get("/projects/{pid}/import-schedules", response_model=List[ImportScheduleOut])
def list_import_schedules(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return [_out(db, t) for t in import_schedule_repo.list_schedules(db, pid)]


@router.post("/projects/{pid}/import-schedules", response_model=ImportScheduleOut)
def create_import_schedule(
    pid: int,
    data: ImportScheduleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    if not (data.url or "").strip():
        raise HTTPException(status_code=400, detail="URL 不能为空")
    try:
        import_schedule_service.validate_fields(
            schedule_type=data.schedule_type,
            run_time=data.run_time,
            week_day=data.week_day,
            interval_minutes=data.interval_minutes,
            cron_expr=data.cron_expr,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    task = ApifoxImportSchedule(
        project_id=pid,
        name=data.name,
        url=data.url.strip(),
        basic_auth_user=data.basic_auth_user or None,
        basic_auth_pwd=data.basic_auth_pwd or None,
        git_token=data.git_token or None,
        delete_unreferenced=data.delete_unreferenced,
        schedule_type=data.schedule_type,
        run_time=data.run_time or "09:00",
        week_day=data.week_day,
        interval_minutes=data.interval_minutes,
        cron_expr=data.cron_expr,
        enabled=data.enabled,
        created_by=user.id,
    )
    _clear_irrelevant(task)
    import_schedule_repo.add(db, task)
    import_schedule_service.refresh_schedule(db, task, force_from_now=True)
    return _out(db, task)


@router.put("/import-schedules/{sid}", response_model=ImportScheduleOut)
def update_import_schedule(
    sid: int,
    data: ImportScheduleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = _owned(db, sid, user)
    payload = data.model_dump(exclude_unset=True)
    # 空字符串的凭据字段视为「不改」，保留已存值
    for key in _SECRET_FIELDS:
        if key in payload and not payload[key]:
            payload.pop(key)

    schedule_type = payload.get("schedule_type", task.schedule_type)
    try:
        import_schedule_service.validate_fields(
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
    _clear_irrelevant(task)
    import_schedule_service.refresh_schedule(db, task, force_from_now=True)
    return _out(db, task)


@router.delete("/import-schedules/{sid}", status_code=204)
def delete_import_schedule(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _owned(db, sid, user)
    import_schedule_repo.delete(db, task)
    db.commit()
    return None


@router.post("/import-schedules/{sid}/run-now", response_model=ImportScheduleOut)
def run_import_schedule_now(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _owned(db, sid, user)
    import_schedule_service.execute_schedule(db, task)
    db.refresh(task)
    return _out(db, task)

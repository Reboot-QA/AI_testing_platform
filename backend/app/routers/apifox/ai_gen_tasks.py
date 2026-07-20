"""Apifox AI 生成任务 · 路由（项目作用域；建/查/取消/勾选入库）。

建任务即返回（后台 worker 执行），前端轮询 GET 拿进度、可恢复。router 只做校验/编排。
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.ai_gen_task import ApifoxAiGenTask, ApifoxAiGenTaskItem
from app.models.user import User
from app.repositories.apifox import ai_gen_task_repo as repo
from app.routers.apifox.ai_gen_task_schemas import (
    AiGenApplyRequest,
    AiGenApplyResult,
    AiGenTaskBrief,
    AiGenTaskCreate,
    AiGenTaskOut,
    AiGenTaskPageOut,
)
from app.services.apifox import ai_gen_task_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·AI生成任务"])


def _task_checked(db: Session, tid: int, user: User) -> ApifoxAiGenTask:
    task = repo.get_task(db, tid)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    get_accessible_project(db, task.project_id, user)
    return task


def _item_checked(db: Session, tid: int, iid: int, user: User) -> ApifoxAiGenTaskItem:
    _task_checked(db, tid, user)
    item = repo.get_item(db, iid)
    if not item or item.task_id != tid:
        raise HTTPException(status_code=404, detail="任务项不存在")
    return item


@router.post("/projects/{pid}/ai-gen-tasks", response_model=AiGenTaskOut)
def create_ai_gen_task(
    pid: int,
    data: AiGenTaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    try:
        task = service.create_task(db, pid, user.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return service.task_out(db, task)


@router.get("/projects/{pid}/ai-gen-tasks/active", response_model=List[AiGenTaskBrief])
def list_active_ai_gen_tasks(
    pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    return service.list_active(db, pid)


@router.get("/projects/{pid}/ai-gen-tasks", response_model=AiGenTaskPageOut)
def list_ai_gen_tasks(
    pid: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    return service.list_tasks_page(db, pid, page, page_size)


@router.get("/ai-gen-tasks/{tid}", response_model=AiGenTaskOut)
def get_ai_gen_task(tid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = _task_checked(db, tid, user)
    return service.task_out(db, task)


@router.post("/ai-gen-tasks/{tid}/cancel", response_model=AiGenTaskOut)
def cancel_ai_gen_task(
    tid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    task = _task_checked(db, tid, user)
    task = service.cancel_task(db, task)
    return service.task_out(db, task)


@router.post("/ai-gen-tasks/{tid}/items/{iid}/apply", response_model=AiGenApplyResult)
def apply_ai_gen_task_item(
    tid: int,
    iid: int,
    data: AiGenApplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = _item_checked(db, tid, iid, user)
    if item.status != "succeeded":
        raise HTTPException(status_code=400, detail="该接口尚未生成成功，无法入库")
    try:
        return service.apply_item(db, item, data.indexes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ai-gen-tasks/{tid}/items/{iid}/retry", response_model=AiGenTaskOut)
def retry_ai_gen_task_item(
    tid: int, iid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    task = _task_checked(db, tid, user)
    item = _item_checked(db, tid, iid, user)
    try:
        task = service.retry_item(db, task, item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return service.task_out(db, task)

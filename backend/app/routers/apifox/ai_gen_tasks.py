"""Apifox AI 生成任务 · 路由（项目作用域；建/查/取消/勾选入库）。

建任务即返回（后台 worker 执行），前端轮询 GET 拿进度、可恢复。router 只做校验/编排。
"""

from datetime import date
from typing import List, Optional

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
    AiGenBatchApplyRequest,
    AiGenBatchApplyResult,
    AiGenDiscardResult,
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


@router.get("/ai-gen-tasks/mine/active", response_model=List[AiGenTaskBrief])
def list_my_active_ai_gen_tasks(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """当前用户跨所有可访问项目的进行中 AI 生成任务（侧边栏角标）。"""
    return service.list_active_mine(db, user)


@router.get("/projects/{pid}/ai-gen-tasks", response_model=AiGenTaskPageOut)
def list_ai_gen_tasks(
    pid: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    keyword: Optional[str] = Query(None, max_length=200, description="模糊匹配 创建人 / 任务接口 method+path"),
    status: Optional[str] = Query(None, description="按任务状态过滤"),
    date_from: Optional[date] = Query(None, description="创建时间下界（含当天）"),
    date_to: Optional[date] = Query(None, description="创建时间上界（含当天）"),
    task_id: Optional[int] = Query(None, ge=1, description="按任务 ID 精确查询"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    return service.list_tasks_page(
        db, pid, page, page_size, keyword, status, date_from, date_to, task_id
    )


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


@router.post("/ai-gen-tasks/{tid}/apply", response_model=AiGenBatchApplyResult)
def apply_ai_gen_task_batch(
    tid: int,
    data: AiGenBatchApplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """一次入库多个接口项：省去前端逐项串行调用，服务端聚合返回最新任务。"""
    task = _task_checked(db, tid, user)
    try:
        return service.apply_items(db, task, data.items)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/ai-gen-tasks/{tid}/items/{iid}/discard", response_model=AiGenDiscardResult)
def discard_ai_gen_task_item(
    tid: int,
    iid: int,
    data: AiGenApplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """从生成预览中废弃用例（未入库）；与 apply 相同 indexes 语义。"""
    item = _item_checked(db, tid, iid, user)
    if item.status != "succeeded":
        raise HTTPException(status_code=400, detail="该接口尚未生成成功")
    try:
        n = service.discard_item(db, item, data.indexes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AiGenDiscardResult(discarded=n)


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

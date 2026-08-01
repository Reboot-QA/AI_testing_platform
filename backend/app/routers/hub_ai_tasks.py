"""平台 AI 任务（需求解析 / 功能用例）列表与详情。"""

import json
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import ensure_menu_permission, get_current_user
from app.database import get_db
from app.models.hub_ai_task import HUB_AI_TASK_TYPES
from app.models.user import User
from app.routers.hub_ai_task_schemas import (
    HubAiTaskBrief,
    HubAiTaskCaseBrief,
    HubAiTaskCasesOut,
    HubAiTaskOut,
    HubAiTaskPageOut,
    HubAiTaskRequirementDiscard,
    HubAiTaskRequirementDiscardResponse,
    HubAiTaskRequirementsOut,
)
from app.services import hub_ai_task_service as service
from app.services.project_access_service import get_accessible_project

TASK_PERMISSION = {
    "requirement": "requirement_docs",
    "functional": "ai_generate",
}


def _ensure_task_permission(db: Session, user: User, task_type: str) -> None:
    menu_key = TASK_PERMISSION.get(task_type)
    if not menu_key:
        raise HTTPException(status_code=400, detail="无效的任务类型")
    ensure_menu_permission(db, user, menu_key)

router = APIRouter(prefix="/projects", tags=["AI任务·需求/用例"])


def _brief(db: Session, task) -> HubAiTaskBrief:
    return HubAiTaskBrief(**service.task_brief(db, task))


@router.get("/{pid}/hub-ai-tasks", response_model=HubAiTaskPageOut)
def list_hub_ai_tasks(
    pid: int,
    task_type: str = Query(..., description="requirement | functional"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    keyword: Optional[str] = Query(None, max_length=200),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    task_id: Optional[int] = Query(None, ge=1, description="按任务 ID 精确查询"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    if task_type not in HUB_AI_TASK_TYPES:
        raise HTTPException(status_code=400, detail="无效的任务类型")
    _ensure_task_permission(db, user, task_type)
    service.fail_stale_running_tasks(db, project_id=pid)
    filters = dict(
        keyword=keyword,
        status=status,
        date_from=date_from,
        date_to=date_to,
        task_id=task_id,
    )
    total = service.count_tasks(db, pid, task_type, **filters)
    rows = service.list_tasks_page(db, pid, task_type, page, page_size, **filters)
    return HubAiTaskPageOut(total=total, items=[_brief(db, r) for r in rows])


@router.get("/{pid}/hub-ai-tasks/{task_id}", response_model=HubAiTaskOut)
def get_hub_ai_task(
    pid: int,
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    service.fail_stale_running_tasks(db, project_id=pid)
    task = service.get_task(db, task_id)
    if not task or task.project_id != pid:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_permission(db, user, task.task_type)
    if task.task_type == "requirement":
        service.sync_unimported_requirement_items(db, task.id)
        db.refresh(task)
    data = service.task_brief(db, task)
    meta = None
    if task.meta_json:
        try:
            meta = json.loads(task.meta_json)
        except json.JSONDecodeError:
            meta = None
    requirements = None
    if task.task_type == "requirement":
        requirements = service.list_requirement_items(db, task.id)
    return HubAiTaskOut(**data, meta=meta, requirements=requirements)


@router.post("/{pid}/hub-ai-tasks/{task_id}/cancel", response_model=HubAiTaskBrief)
def cancel_hub_ai_task(
    pid: int,
    task_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    task = service.get_task(db, task_id)
    if not task or task.project_id != pid:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_permission(db, user, task.task_type)
    canceled = service.cancel_hub_task(db, task_id)
    if not canceled:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _brief(db, canceled)


@router.get("/{pid}/hub-ai-tasks/{task_id}/requirements", response_model=HubAiTaskRequirementsOut)
def list_hub_ai_task_requirements(
    pid: int,
    task_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    service.fail_stale_running_tasks(db, project_id=pid)
    task = service.get_task(db, task_id)
    if not task or task.project_id != pid:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_permission(db, user, task.task_type)
    if task.task_type != "requirement":
        raise HTTPException(status_code=400, detail="该任务不是需求解析任务")
    items, total = service.list_requirement_items_page(db, task.id, page=page, page_size=page_size)
    return HubAiTaskRequirementsOut(items=items, total=total)


@router.post(
    "/{pid}/hub-ai-tasks/{task_id}/requirements/discard",
    response_model=HubAiTaskRequirementDiscardResponse,
)
def discard_hub_ai_task_requirements(
    pid: int,
    task_id: int,
    body: HubAiTaskRequirementDiscard,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    task = service.get_task(db, task_id)
    if not task or task.project_id != pid:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_permission(db, user, task.task_type)
    if task.task_type != "requirement":
        raise HTTPException(status_code=400, detail="该任务不是需求解析任务")
    discarded = service.discard_requirement_items(
        db, task_id, project_id=pid, item_ids=body.item_ids
    )
    if not discarded and body.item_ids:
        raise HTTPException(status_code=400, detail="无法废弃：条目不存在或已入库")
    return HubAiTaskRequirementDiscardResponse(
        discarded=discarded,
        message=f"已废弃 {discarded} 条需求点",
    )


@router.get("/{pid}/hub-ai-tasks/{task_id}/cases", response_model=HubAiTaskCasesOut)
def list_hub_ai_task_cases(
    pid: int,
    task_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    service.fail_stale_running_tasks(db, project_id=pid)
    task = service.get_task(db, task_id)
    if not task or task.project_id != pid:
        raise HTTPException(status_code=404, detail="任务不存在")
    _ensure_task_permission(db, user, task.task_type)
    if task.task_type != "functional":
        raise HTTPException(status_code=400, detail="该任务不是 AI 用例生成任务")
    raw, total = service.list_case_items_page(db, task.id, page=page, page_size=page_size)
    items = [HubAiTaskCaseBrief(**row) for row in raw]
    return HubAiTaskCasesOut(items=items, total=total)

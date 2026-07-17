"""Apifox AI 生成任务 · 业务层（建任务/序列化/查询/取消/apply 入库）。

worker 执行循环在 ai_gen_worker.py；本模块只做无副作用编排与 DB 读写（末尾 commit）。
"""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.ai_gen_task import ApifoxAiGenTask, ApifoxAiGenTaskItem
from app.repositories.apifox import ai_gen_task_repo as repo
from app.repositories.apifox import endpoint_repo
from app.routers.apifox.ai_gen_task_schemas import (
    AiGenApplyResult,
    AiGenTaskBrief,
    AiGenTaskCreate,
    AiGenTaskItemOut,
    AiGenTaskOut,
    AiGenTaskPageOut,
)
from app.routers.apifox.case_schemas import AiGenCategory, CaseCreate
from app.services.apifox import case_service

_TERMINAL = ("succeeded", "partial", "failed", "canceled")


# ---------- 序列化（worker 与 service 共用） ----------
def dump_categories(cats: List[AiGenCategory]) -> str:
    return json.dumps([c.model_dump() for c in cats], ensure_ascii=False)


def load_categories(text: str) -> List[AiGenCategory]:
    return [AiGenCategory(**x) for x in json.loads(text or "[]")]


def dump_cases(cases: List[CaseCreate]) -> str:
    return json.dumps([c.model_dump() for c in cases], ensure_ascii=False)


def load_cases(text: Optional[str]) -> List[CaseCreate]:
    if not text:
        return []
    try:
        return [CaseCreate(**x) for x in json.loads(text)]
    except (ValueError, TypeError):
        return []


# ---------- 建任务 ----------
def create_task(
    db: Session, project_id: int, created_by: Optional[int], data: AiGenTaskCreate
) -> ApifoxAiGenTask:
    endpoints = [endpoint_repo.get_endpoint(db, eid) for eid in dict.fromkeys(data.endpoint_ids)]
    valid = [e for e in endpoints if e and e.project_id == project_id]
    if not valid:
        raise ValueError("没有可用于生成的接口（不存在或不属于该项目）")

    task = ApifoxAiGenTask(
        project_id=project_id,
        created_by=created_by,
        status="pending",
        provider_id=data.provider_id,
        categories=dump_categories(data.categories),
        total_items=len(valid),
        done_items=0,
    )
    repo.add(db, task)
    for ep in valid:
        repo.add(db, ApifoxAiGenTaskItem(task_id=task.id, endpoint_id=ep.id, status="pending"))
    db.commit()
    db.refresh(task)
    return task


# ---------- 查询 ----------
def _item_out(db: Session, item: ApifoxAiGenTaskItem) -> AiGenTaskItemOut:
    ep = endpoint_repo.get_endpoint(db, item.endpoint_id)
    return AiGenTaskItemOut(
        id=item.id,
        endpoint_id=item.endpoint_id,
        endpoint_name=ep.name if ep else "(接口已删除)",
        endpoint_method=ep.method if ep else "",
        status=item.status,
        generated_count=item.generated_count,
        applied_count=item.applied_count,
        error=item.error,
        cases=load_cases(item.result_cases),
    )


def task_out(db: Session, task: ApifoxAiGenTask) -> AiGenTaskOut:
    return AiGenTaskOut(
        id=task.id,
        project_id=task.project_id,
        status=task.status,
        mode=task.mode,
        provider_id=task.provider_id,
        total_items=task.total_items,
        done_items=task.done_items,
        error=task.error,
        created_at=task.created_at,
        finished_at=task.finished_at,
        items=[_item_out(db, it) for it in repo.list_items(db, task.id)],
    )


def _brief(task: ApifoxAiGenTask) -> AiGenTaskBrief:
    return AiGenTaskBrief(
        id=task.id, status=task.status, mode=task.mode,
        total_items=task.total_items, done_items=task.done_items, created_at=task.created_at,
    )


def list_active(db: Session, project_id: int) -> List[AiGenTaskBrief]:
    return [_brief(t) for t in repo.list_active_tasks(db, project_id)]


def list_tasks_page(db: Session, project_id: int, page: int, page_size: int) -> AiGenTaskPageOut:
    return AiGenTaskPageOut(
        items=[_brief(t) for t in repo.list_project_tasks_page(db, project_id, page, page_size)],
        total=repo.count_project_tasks(db, project_id),
        page=page,
        page_size=page_size,
    )


# ---------- 取消 ----------
def cancel_task(db: Session, task: ApifoxAiGenTask) -> ApifoxAiGenTask:
    if task.status in _TERMINAL:
        return task  # 已终态，幂等
    task.status = "canceled"
    task.finished_at = datetime.utcnow()
    for item in repo.list_items(db, task.id):
        if item.status in ("pending", "running"):
            item.status = "canceled"
    db.commit()
    db.refresh(task)
    return task


# ---------- 重试失败接口 ----------
def retry_item(db: Session, task: ApifoxAiGenTask, item: ApifoxAiGenTaskItem) -> ApifoxAiGenTask:
    """重试某个失败接口：该 item 复位 pending、整任务复位 pending 交 worker 重跑。

    仅任务已结束 + 该接口失败时可重试（避免与运行中的 worker 抢状态）。
    """
    if task.status not in _TERMINAL:
        raise ValueError("任务尚未结束，无法重试")
    if item.status != "failed":
        raise ValueError("仅失败的接口可重试")
    item.status = "pending"
    item.error = None
    item.result_cases = None
    item.generated_count = 0
    task.status = "pending"
    task.finished_at = None
    task.done_items = max(0, task.done_items - 1)  # worker 重处理该 item 会再 +1
    db.commit()
    db.refresh(task)
    return task


# ---------- 勾选入库 ----------
def apply_item(
    db: Session, item: ApifoxAiGenTaskItem, indexes: Optional[List[int]]
) -> AiGenApplyResult:
    cases = load_cases(item.result_cases)
    if indexes is not None:
        cases = [cases[i] for i in indexes if 0 <= i < len(cases)]
    endpoint = endpoint_repo.get_endpoint(db, item.endpoint_id)
    if not endpoint:
        raise ValueError("接口不存在")

    created = 0
    failed: List[str] = []
    for case in cases:
        try:
            case_service.create_case(db, endpoint.project_id, endpoint.id, case)
            created += 1
        except (ValueError, TypeError):
            failed.append(case.name)
    item.applied_count += created
    db.commit()
    return AiGenApplyResult(created=created, failed=failed)

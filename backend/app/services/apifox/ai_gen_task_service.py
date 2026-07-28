"""Apifox AI 生成任务 · 业务层（建任务/序列化/查询/取消/apply 入库）。

worker 执行循环在 ai_gen_worker.py；本模块只做无副作用编排与 DB 读写（末尾 commit）。
"""

import json
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.ai_gen_task import ApifoxAiGenTask, ApifoxAiGenTaskItem
from app.models.llm_provider import LLMProvider
from app.models.user import User
from app.repositories.apifox import ai_gen_task_repo as repo
from app.repositories.apifox import endpoint_repo
from app.routers.apifox.ai_gen_task_schemas import (
    AiGenApplyResult,
    AiGenBatchApplyItem,
    AiGenBatchApplyResult,
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
        discarded_cases=load_cases(item.discarded_cases),
    )


def _creator_name(db: Session, created_by: Optional[int]) -> Optional[str]:
    if not created_by:
        return None
    user = db.query(User).filter(User.id == created_by).first()
    return user.username if user else None


def _provider_name(db: Session, provider_id: Optional[int]) -> Optional[str]:
    if not provider_id:
        return None
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    return provider.name if provider else None


def task_out(db: Session, task: ApifoxAiGenTask) -> AiGenTaskOut:
    return AiGenTaskOut(
        id=task.id,
        project_id=task.project_id,
        status=task.status,
        mode=task.mode,
        provider_id=task.provider_id,
        provider_name=_provider_name(db, task.provider_id),
        categories=load_categories(task.categories),
        creator_name=_creator_name(db, task.created_by),
        total_items=task.total_items,
        done_items=task.done_items,
        error=task.error,
        created_at=task.created_at,
        finished_at=task.finished_at,
        items=[_item_out(db, it) for it in repo.list_items(db, task.id)],
    )


def _brief(
    task: ApifoxAiGenTask,
    target: Optional[str] = None,
    categories: Optional[List[str]] = None,
    generated_total: int = 0,
    applied_total: int = 0,
    creator_name: Optional[str] = None,
) -> AiGenTaskBrief:
    return AiGenTaskBrief(
        id=task.id, status=task.status, mode=task.mode,
        target=target, categories=categories or [],
        generated_total=generated_total, applied_total=applied_total,
        creator_name=creator_name,
        total_items=task.total_items, done_items=task.done_items,
        created_at=task.created_at, finished_at=task.finished_at,
    )


def _creator_names(db: Session, user_ids: List[Optional[int]]) -> dict[int, str]:
    ids = {uid for uid in user_ids if uid}
    if not ids:
        return {}
    return {
        u.id: u.username
        for u in db.query(User).filter(User.id.in_(ids)).all()
        if u.username
    }


def list_active(db: Session, project_id: int) -> List[AiGenTaskBrief]:
    tasks = repo.list_active_tasks(db, project_id)
    names = _creator_names(db, [t.created_by for t in tasks])
    return [
        _brief(t, creator_name=names.get(t.created_by) if t.created_by else None)
        for t in tasks
    ]


def _task_target(db: Session, task: ApifoxAiGenTask, items: List[ApifoxAiGenTaskItem]) -> Optional[str]:
    """单接口任务→该接口 method+path；批量→None（前端展示"批量·N接口"）。"""
    if task.total_items != 1 or not items:
        return None
    endpoint = endpoint_repo.get_endpoint(db, items[0].endpoint_id)
    return f"{endpoint.method} {endpoint.path}" if endpoint else "(接口已删除)"


def list_tasks_page(
    db: Session,
    project_id: int,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> AiGenTaskPageOut:
    tasks = repo.list_project_tasks_page(
        db, project_id, page, page_size, keyword, status, date_from, date_to
    )
    items_by_task: dict[int, List[ApifoxAiGenTaskItem]] = {}
    for it in repo.list_items_by_task_ids(db, [t.id for t in tasks]):
        items_by_task.setdefault(it.task_id, []).append(it)
    names = _creator_names(db, [t.created_by for t in tasks])

    briefs = []
    for t in tasks:
        its = items_by_task.get(t.id, [])
        briefs.append(_brief(
            t,
            target=_task_target(db, t, its),
            categories=[c.category for c in load_categories(t.categories)],
            generated_total=sum(i.generated_count for i in its),
            applied_total=sum(i.applied_count for i in its),
            creator_name=names.get(t.created_by) if t.created_by else None,
        ))
    return AiGenTaskPageOut(
        items=briefs,
        total=repo.count_project_tasks(db, project_id, keyword, status, date_from, date_to),
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
    item.discarded_cases = None
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
    all_cases = load_cases(item.result_cases)
    if indexes is not None:
        cases = [all_cases[i] for i in indexes if 0 <= i < len(all_cases)]
    else:
        cases = list(all_cases)
    endpoint = endpoint_repo.get_endpoint(db, item.endpoint_id)
    if not endpoint:
        raise ValueError("接口不存在")

    # 批量入库：同名跳过 + 单次提交（避免逐条 commit 拖慢）
    created, skipped, failed = case_service.create_cases_bulk(
        db, endpoint.project_id, endpoint.id, cases, origin="ai"
    )
    item.applied_count += created
    failed_names = set(failed)
    if indexes is not None:
        drop = {
            i
            for i in indexes
            if 0 <= i < len(all_cases) and all_cases[i].name not in failed_names
        }
    else:
        drop = {i for i, c in enumerate(all_cases) if c.name not in failed_names}
    remaining = [c for i, c in enumerate(all_cases) if i not in drop]
    item.result_cases = dump_cases(remaining) if remaining else None
    item.generated_count = len(remaining)
    db.commit()
    return AiGenApplyResult(created=created, failed=failed, skipped=skipped)


def apply_items(
    db: Session, task: ApifoxAiGenTask, specs: List[AiGenBatchApplyItem]
) -> AiGenBatchApplyResult:
    """一次请求入库多个接口项，聚合结果（省去前端逐项串行往返）。"""
    created = 0
    skipped = 0
    failed: List[str] = []
    applied_items = 0
    for spec in specs:
        item = repo.get_item(db, spec.item_id)
        if not item or item.task_id != task.id or item.status != "succeeded":
            continue  # 不属于该任务/未生成成功的项跳过，不打断其余
        res = apply_item(db, item, spec.indexes)
        created += res.created
        skipped += res.skipped
        failed += res.failed
        applied_items += 1
    return AiGenBatchApplyResult(
        created=created,
        skipped=skipped,
        failed=failed,
        applied_items=applied_items,
        task=task_out(db, task),
    )


def discard_item(
    db: Session, item: ApifoxAiGenTaskItem, indexes: Optional[List[int]]
) -> int:
    """从任务预览中移除生成用例（未入库）；不删接口用例表。"""
    cases = load_cases(item.result_cases)
    if not cases:
        return 0
    if item.applied_count > 0:
        raise ValueError("该接口已有入库记录，无法废弃预览")
    if indexes is not None:
        drop = {i for i in indexes if 0 <= i < len(cases)}
        removed = [c for i, c in enumerate(cases) if i in drop]
        remaining = [c for i, c in enumerate(cases) if i not in drop]
    else:
        removed = list(cases)
        remaining = []
    discarded = len(cases) - len(remaining)
    if removed:
        archived = load_cases(item.discarded_cases) + removed
        item.discarded_cases = dump_cases(archived)
    item.result_cases = dump_cases(remaining) if remaining else None
    item.generated_count = len(remaining)
    db.commit()
    return discarded

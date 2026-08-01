"""Apifox AI 生成任务 · 数据访问层（无业务校验/权限；不提交事务，由 service/worker commit）。"""

from datetime import date, datetime, time, timedelta
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.apifox.ai_gen_task import ApifoxAiGenTask, ApifoxAiGenTaskItem
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.user import User


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def get_task(db: Session, task_id: int) -> Optional[ApifoxAiGenTask]:
    return db.query(ApifoxAiGenTask).filter(ApifoxAiGenTask.id == task_id).first()


def get_item(db: Session, item_id: int) -> Optional[ApifoxAiGenTaskItem]:
    return db.query(ApifoxAiGenTaskItem).filter(ApifoxAiGenTaskItem.id == item_id).first()


def list_items_by_task_ids(db: Session, task_ids: List[int]) -> List[ApifoxAiGenTaskItem]:
    if not task_ids:
        return []
    return (
        db.query(ApifoxAiGenTaskItem)
        .filter(ApifoxAiGenTaskItem.task_id.in_(task_ids))
        .all()
    )


def list_items(db: Session, task_id: int) -> List[ApifoxAiGenTaskItem]:
    return (
        db.query(ApifoxAiGenTaskItem)
        .filter(ApifoxAiGenTaskItem.task_id == task_id)
        .order_by(ApifoxAiGenTaskItem.id)
        .all()
    )


def list_active_tasks(db: Session, project_id: int) -> List[ApifoxAiGenTask]:
    """项目进行中任务（pending/running），供前端进工作区时恢复进度。"""
    return (
        db.query(ApifoxAiGenTask)
        .filter(
            ApifoxAiGenTask.project_id == project_id,
            ApifoxAiGenTask.status.in_(("pending", "running")),
        )
        .order_by(ApifoxAiGenTask.id.desc())
        .all()
    )


def list_active_tasks_for_creator(
    db: Session, *, creator_id: int, project_ids: List[int]
) -> List[ApifoxAiGenTask]:
    """当前用户在可访问项目内进行中的 AI 生成任务（跨项目，供全局角标）。"""
    if not project_ids:
        return []
    return (
        db.query(ApifoxAiGenTask)
        .filter(
            ApifoxAiGenTask.project_id.in_(project_ids),
            ApifoxAiGenTask.created_by == creator_id,
            ApifoxAiGenTask.status.in_(("pending", "running")),
        )
        .order_by(ApifoxAiGenTask.id.desc())
        .all()
    )


def list_project_tasks(db: Session, project_id: int, limit: int = 20) -> List[ApifoxAiGenTask]:
    return (
        db.query(ApifoxAiGenTask)
        .filter(ApifoxAiGenTask.project_id == project_id)
        .order_by(ApifoxAiGenTask.id.desc())
        .limit(limit)
        .all()
    )


def _filtered_tasks_query(
    db: Session,
    project_id: int,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    task_id: Optional[int] = None,
):
    """项目任务列表的统一过滤（count 与 page 共用，保证 total 与 items 一致）。"""
    query = db.query(ApifoxAiGenTask).filter(ApifoxAiGenTask.project_id == project_id)
    if task_id is not None:
        query = query.filter(ApifoxAiGenTask.id == task_id)
    if status:
        query = query.filter(ApifoxAiGenTask.status == status)
    if date_from:
        query = query.filter(ApifoxAiGenTask.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        # 闭区间：含 date_to 当天全天，故上界取次日零点开区间
        query = query.filter(
            ApifoxAiGenTask.created_at < datetime.combine(date_to, time.min) + timedelta(days=1)
        )
    if keyword and keyword.strip():
        like = f"%{keyword.strip()}%"
        # target(单接口任务 method+path) 与 creator_name(created_by→users) 均为派生值、非本表列，
        # 故用子查询命中：命中创建人，或命中任务所含接口的 method/path。
        creator_ids = select(User.id).where(
            or_(User.full_name.like(like), User.username.like(like))
        )
        target_task_ids = (
            select(ApifoxAiGenTaskItem.task_id)
            .join(ApifoxEndpoint, ApifoxEndpoint.id == ApifoxAiGenTaskItem.endpoint_id)
            .where(or_(ApifoxEndpoint.method.like(like), ApifoxEndpoint.path.like(like)))
        )
        query = query.filter(
            or_(
                ApifoxAiGenTask.created_by.in_(creator_ids),
                ApifoxAiGenTask.id.in_(target_task_ids),
            )
        )
    return query


def count_project_tasks(
    db: Session,
    project_id: int,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    task_id: Optional[int] = None,
) -> int:
    return _filtered_tasks_query(
        db, project_id, keyword, status, date_from, date_to, task_id
    ).count()


def list_project_tasks_page(
    db: Session,
    project_id: int,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    task_id: Optional[int] = None,
) -> List[ApifoxAiGenTask]:
    return (
        _filtered_tasks_query(db, project_id, keyword, status, date_from, date_to, task_id)
        .order_by(ApifoxAiGenTask.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )


def claim_next_pending(db: Session) -> Optional[ApifoxAiGenTask]:
    """worker 取一个待处理任务：同模型同时仅 1 个 running，不同模型可并行。"""
    running = db.query(ApifoxAiGenTask).filter(ApifoxAiGenTask.status == "running").all()
    busy_providers = {
        int(t.provider_id) if t.provider_id is not None else 0 for t in running
    }

    pending = (
        db.query(ApifoxAiGenTask)
        .filter(ApifoxAiGenTask.status == "pending")
        .order_by(ApifoxAiGenTask.id)
        .all()
    )
    for task in pending:
        key = int(task.provider_id) if task.provider_id is not None else 0
        if key not in busy_providers:
            return task
    return None


def reset_running_to_pending(db: Session) -> int:
    """启动恢复：把残留 running（上次进程崩溃遗留）重置为 pending 以便 worker 重跑。"""
    n = (
        db.query(ApifoxAiGenTask)
        .filter(ApifoxAiGenTask.status == "running")
        .update({ApifoxAiGenTask.status: "pending"}, synchronize_session=False)
    )
    db.query(ApifoxAiGenTaskItem).filter(ApifoxAiGenTaskItem.status == "running").update(
        {ApifoxAiGenTaskItem.status: "pending"}, synchronize_session=False
    )
    return n

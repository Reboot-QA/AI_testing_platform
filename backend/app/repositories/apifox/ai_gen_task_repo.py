"""Apifox AI 生成任务 · 数据访问层（无业务校验/权限；不提交事务，由 service/worker commit）。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.ai_gen_task import ApifoxAiGenTask, ApifoxAiGenTaskItem


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def get_task(db: Session, task_id: int) -> Optional[ApifoxAiGenTask]:
    return db.query(ApifoxAiGenTask).filter(ApifoxAiGenTask.id == task_id).first()


def get_item(db: Session, item_id: int) -> Optional[ApifoxAiGenTaskItem]:
    return db.query(ApifoxAiGenTaskItem).filter(ApifoxAiGenTaskItem.id == item_id).first()


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


def list_project_tasks(db: Session, project_id: int, limit: int = 20) -> List[ApifoxAiGenTask]:
    return (
        db.query(ApifoxAiGenTask)
        .filter(ApifoxAiGenTask.project_id == project_id)
        .order_by(ApifoxAiGenTask.id.desc())
        .limit(limit)
        .all()
    )


def claim_next_pending(db: Session) -> Optional[ApifoxAiGenTask]:
    """worker 取一个待处理任务（按 id 升序，先到先跑）。单 worker 线程，无需行锁。"""
    return (
        db.query(ApifoxAiGenTask)
        .filter(ApifoxAiGenTask.status == "pending")
        .order_by(ApifoxAiGenTask.id)
        .first()
    )


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

"""Apifox 定时任务 · 数据访问层。不含业务校验；不提交事务（由 service commit）。"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.schedule import ApifoxSchedule


def list_schedules(db: Session, project_id: int) -> List[ApifoxSchedule]:
    return (
        db.query(ApifoxSchedule)
        .filter(ApifoxSchedule.project_id == project_id)
        .order_by(ApifoxSchedule.id.desc())
        .all()
    )


def get_schedule(db: Session, schedule_id: int) -> Optional[ApifoxSchedule]:
    return db.query(ApifoxSchedule).filter(ApifoxSchedule.id == schedule_id).first()


def list_due(db: Session, now: datetime) -> List[ApifoxSchedule]:
    return (
        db.query(ApifoxSchedule)
        .filter(
            ApifoxSchedule.enabled.is_(True),
            ApifoxSchedule.next_run_at.isnot(None),
            ApifoxSchedule.next_run_at <= now,
        )
        .all()
    )


def add(db: Session, obj: ApifoxSchedule) -> ApifoxSchedule:
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj: ApifoxSchedule) -> None:
    db.delete(obj)

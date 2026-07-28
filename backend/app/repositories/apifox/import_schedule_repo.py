"""Apifox 定时导入 · 数据访问层。不含业务校验；不提交事务（由 service commit）。"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.import_schedule import ApifoxImportSchedule


def list_schedules(db: Session, project_id: int) -> List[ApifoxImportSchedule]:
    return (
        db.query(ApifoxImportSchedule)
        .filter(ApifoxImportSchedule.project_id == project_id)
        .order_by(ApifoxImportSchedule.id.desc())
        .all()
    )


def get_schedule(db: Session, schedule_id: int) -> Optional[ApifoxImportSchedule]:
    return db.query(ApifoxImportSchedule).filter(ApifoxImportSchedule.id == schedule_id).first()


def list_due(db: Session, now: datetime) -> List[ApifoxImportSchedule]:
    return (
        db.query(ApifoxImportSchedule)
        .filter(
            ApifoxImportSchedule.enabled.is_(True),
            ApifoxImportSchedule.next_run_at.isnot(None),
            ApifoxImportSchedule.next_run_at <= now,
        )
        .all()
    )


def add(db: Session, obj: ApifoxImportSchedule) -> ApifoxImportSchedule:
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj: ApifoxImportSchedule) -> None:
    db.delete(obj)

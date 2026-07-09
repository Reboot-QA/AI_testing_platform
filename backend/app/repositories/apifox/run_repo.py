"""Apifox 运行记录 · 数据访问层。不含业务校验；提交时机由 run_service 控制（流式逐步落库）。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.run import ApifoxRun, ApifoxRunStep


def list_runs(db: Session, project_id: int, limit: int = 100) -> List[ApifoxRun]:
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.project_id == project_id)
        .order_by(ApifoxRun.id.desc())
        .limit(limit)
        .all()
    )


def get_run(db: Session, run_id: int) -> Optional[ApifoxRun]:
    return db.query(ApifoxRun).filter(ApifoxRun.id == run_id).first()


def list_steps(db: Session, run_id: int) -> List[ApifoxRunStep]:
    return (
        db.query(ApifoxRunStep)
        .filter(ApifoxRunStep.run_id == run_id)
        .order_by(ApifoxRunStep.id)
        .all()
    )


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj

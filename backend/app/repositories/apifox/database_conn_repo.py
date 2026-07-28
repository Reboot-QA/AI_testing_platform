"""Apifox 环境数据库连接 · 数据访问层。不含业务校验；不提交事务。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.database_conn import ApifoxEnvironmentDatabase


def list_by_environment(db: Session, environment_id: int) -> List[ApifoxEnvironmentDatabase]:
    return (
        db.query(ApifoxEnvironmentDatabase)
        .filter(ApifoxEnvironmentDatabase.environment_id == environment_id)
        .order_by(ApifoxEnvironmentDatabase.sort_order, ApifoxEnvironmentDatabase.id)
        .all()
    )


def get(db: Session, conn_id: int) -> Optional[ApifoxEnvironmentDatabase]:
    return (
        db.query(ApifoxEnvironmentDatabase)
        .filter(ApifoxEnvironmentDatabase.id == conn_id)
        .first()
    )


def add(db: Session, obj: ApifoxEnvironmentDatabase) -> ApifoxEnvironmentDatabase:
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj: ApifoxEnvironmentDatabase) -> None:
    db.delete(obj)

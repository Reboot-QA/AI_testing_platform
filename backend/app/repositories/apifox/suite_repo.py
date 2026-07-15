"""Apifox 测试套件 · 数据访问层（套件 + 套件项）。不含业务校验；不提交事务。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.suite import ApifoxSuite, ApifoxSuiteItem


def list_suites(db: Session, project_id: int) -> List[ApifoxSuite]:
    return (
        db.query(ApifoxSuite)
        .filter(ApifoxSuite.project_id == project_id)
        .order_by(ApifoxSuite.sort_order, ApifoxSuite.id)
        .all()
    )


def name_exists(db: Session, project_id: int, name: str) -> bool:
    return (
        db.query(ApifoxSuite.id)
        .filter(ApifoxSuite.project_id == project_id, ApifoxSuite.name == name)
        .first()
        is not None
    )


def get_suite(db: Session, suite_id: int) -> Optional[ApifoxSuite]:
    return db.query(ApifoxSuite).filter(ApifoxSuite.id == suite_id).first()


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj) -> None:
    db.delete(obj)


def list_items(db: Session, suite_id: int) -> List[ApifoxSuiteItem]:
    return (
        db.query(ApifoxSuiteItem)
        .filter(ApifoxSuiteItem.suite_id == suite_id)
        .order_by(ApifoxSuiteItem.sort_order, ApifoxSuiteItem.id)
        .all()
    )


def count_items(db: Session, suite_id: int) -> int:
    return db.query(ApifoxSuiteItem).filter(ApifoxSuiteItem.suite_id == suite_id).count()


def delete_items(db: Session, suite_id: int) -> None:
    db.query(ApifoxSuiteItem).filter(ApifoxSuiteItem.suite_id == suite_id).delete(
        synchronize_session=False
    )

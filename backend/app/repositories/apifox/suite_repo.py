"""Apifox 测试套件 · 数据访问层（套件 + 套件项）。不含业务校验；不提交事务。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.suite import ApifoxSuite, ApifoxSuiteItem


def list_suites(db: Session, project_id: int) -> List[ApifoxSuite]:
    return (
        db.query(ApifoxSuite)
        .filter(ApifoxSuite.project_id == project_id, ApifoxSuite.deleted_at.is_(None))
        .order_by(ApifoxSuite.sort_order, ApifoxSuite.id)
        .all()
    )


def list_deleted_suites(db: Session, project_id: int) -> List[ApifoxSuite]:
    """回收站：项目内已软删除的套件（最近删的在前）。"""
    return (
        db.query(ApifoxSuite)
        .filter(ApifoxSuite.project_id == project_id, ApifoxSuite.deleted_at.is_not(None))
        .order_by(ApifoxSuite.deleted_at.desc(), ApifoxSuite.id.desc())
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


def detach_case_refs(db: Session, case_ids: set[int]) -> int:
    """移除套件项中对给定用例的引用（不 commit）。"""
    if not case_ids:
        return 0
    return (
        db.query(ApifoxSuiteItem)
        .filter(ApifoxSuiteItem.target_type == "case", ApifoxSuiteItem.target_id.in_(case_ids))
        .delete(synchronize_session=False)
    )


def list_suites_referencing_case(db: Session, case_id: int) -> List[ApifoxSuite]:
    """把该用例作为 case 项引用的套件（去重）——供 swagger 更新时的引用告警。"""
    return (
        db.query(ApifoxSuite)
        .join(ApifoxSuiteItem, ApifoxSuiteItem.suite_id == ApifoxSuite.id)
        .filter(ApifoxSuiteItem.target_type == "case", ApifoxSuiteItem.target_id == case_id)
        .distinct()
        .all()
    )

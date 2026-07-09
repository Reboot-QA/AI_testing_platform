"""Apifox 接口用例 · 数据访问层（用例 + 断言/提取子表）。

不含业务校验与权限；不提交事务（service commit）。子表 bulk replace 由 service 编排。
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.case import (
    ApifoxCaseAssertion,
    ApifoxCaseExtract,
    ApifoxEndpointCase,
)


def list_cases(db: Session, endpoint_id: int) -> List[ApifoxEndpointCase]:
    return (
        db.query(ApifoxEndpointCase)
        .filter(ApifoxEndpointCase.endpoint_id == endpoint_id)
        .order_by(ApifoxEndpointCase.sort_order, ApifoxEndpointCase.id)
        .all()
    )


def get_case(db: Session, case_id: int) -> Optional[ApifoxEndpointCase]:
    return db.query(ApifoxEndpointCase).filter(ApifoxEndpointCase.id == case_id).first()


def list_assertions(db: Session, case_id: int) -> List[ApifoxCaseAssertion]:
    return (
        db.query(ApifoxCaseAssertion)
        .filter(ApifoxCaseAssertion.case_id == case_id)
        .order_by(ApifoxCaseAssertion.sort_order, ApifoxCaseAssertion.id)
        .all()
    )


def list_extracts(db: Session, case_id: int) -> List[ApifoxCaseExtract]:
    return (
        db.query(ApifoxCaseExtract)
        .filter(ApifoxCaseExtract.case_id == case_id)
        .order_by(ApifoxCaseExtract.sort_order, ApifoxCaseExtract.id)
        .all()
    )


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj) -> None:
    db.delete(obj)


def delete_assertions(db: Session, case_id: int) -> None:
    db.query(ApifoxCaseAssertion).filter(ApifoxCaseAssertion.case_id == case_id).delete(
        synchronize_session=False
    )


def delete_extracts(db: Session, case_id: int) -> None:
    db.query(ApifoxCaseExtract).filter(ApifoxCaseExtract.case_id == case_id).delete(
        synchronize_session=False
    )


def delete_children(db: Session, case_id: int) -> None:
    delete_assertions(db, case_id)
    delete_extracts(db, case_id)

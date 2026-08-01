"""Apifox 接口用例 · 数据访问层（用例 + 断言/提取子表）。

不含业务校验与权限；不提交事务（service commit）。子表 bulk replace 由 service 编排。
"""

from typing import List, Optional

from sqlalchemy import Row
from sqlalchemy.orm import Session

from app.models.apifox.case import (
    ApifoxCaseAssertion,
    ApifoxCaseExtract,
    ApifoxEndpointCase,
)
from app.models.apifox.endpoint import ApifoxEndpoint


def list_project_cases(
    db: Session, project_id: int
) -> List[Row[tuple[ApifoxEndpointCase, ApifoxEndpoint]]]:
    """项目全量用例（带所属接口），场景步骤选择器数据源。返回 (case, endpoint) 元组列表。"""
    return (
        db.query(ApifoxEndpointCase, ApifoxEndpoint)
        .join(ApifoxEndpoint, ApifoxEndpoint.id == ApifoxEndpointCase.endpoint_id)
        .filter(
            ApifoxEndpoint.project_id == project_id,
            ApifoxEndpointCase.deleted_at.is_(None),
            ApifoxEndpoint.deleted_at.is_(None),  # 接口在回收站时，其用例一并从选择器隐藏
        )
        .order_by(ApifoxEndpoint.sort_order, ApifoxEndpoint.id,
                  ApifoxEndpointCase.sort_order, ApifoxEndpointCase.id)
        .all()
    )


def list_all_cases_by_endpoint(db: Session, endpoint_id: int) -> List[ApifoxEndpointCase]:
    """接口下全部用例（含已软删的），供接口彻底删除时级联清理。"""
    return (
        db.query(ApifoxEndpointCase)
        .filter(ApifoxEndpointCase.endpoint_id == endpoint_id)
        .all()
    )


def list_cases_by_project(db: Session, project_id: int) -> List[ApifoxEndpointCase]:
    """项目全量用例（不 JOIN 接口）——供只需用例自身字段(如 data_drive)的扫描用。"""
    return (
        db.query(ApifoxEndpointCase)
        .filter(ApifoxEndpointCase.project_id == project_id, ApifoxEndpointCase.deleted_at.is_(None))
        .all()
    )


def list_deleted_cases(
    db: Session, project_id: int
) -> List[Row[tuple[ApifoxEndpointCase, ApifoxEndpoint]]]:
    """回收站：项目内已软删除的用例（带所属接口，最近删的在前）。"""
    return (
        db.query(ApifoxEndpointCase, ApifoxEndpoint)
        .join(ApifoxEndpoint, ApifoxEndpoint.id == ApifoxEndpointCase.endpoint_id)
        .filter(
            ApifoxEndpointCase.project_id == project_id,
            ApifoxEndpointCase.deleted_at.is_not(None),
        )
        .order_by(ApifoxEndpointCase.deleted_at.desc(), ApifoxEndpointCase.id.desc())
        .all()
    )


def list_cases(db: Session, endpoint_id: int) -> List[ApifoxEndpointCase]:
    return (
        db.query(ApifoxEndpointCase)
        .filter(ApifoxEndpointCase.endpoint_id == endpoint_id, ApifoxEndpointCase.deleted_at.is_(None))
        .order_by(ApifoxEndpointCase.sort_order, ApifoxEndpointCase.id)
        .all()
    )


def list_cases_all(db: Session, endpoint_id: int) -> List[ApifoxEndpointCase]:
    """接口下所有用例（含回收站里已软删的）——硬删接口时须清空子表，否则残留
    endpoint_id 外键，在 MySQL 上触发 1451 外键约束报错。"""
    return db.query(ApifoxEndpointCase).filter(ApifoxEndpointCase.endpoint_id == endpoint_id).all()


def name_exists(db: Session, endpoint_id: int, name: str) -> bool:
    return (
        db.query(ApifoxEndpointCase.id)
        .filter(ApifoxEndpointCase.endpoint_id == endpoint_id, ApifoxEndpointCase.name == name)
        .first()
        is not None
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

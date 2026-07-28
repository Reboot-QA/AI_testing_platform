"""Apifox 脚本库 · 数据访问层（脚本 + 用例前后置关联）。不含业务校验；不提交事务。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.script import ApifoxCaseScript, ApifoxEndpointScript, ApifoxScript


def list_scripts(db: Session, project_id: int) -> List[ApifoxScript]:
    return (
        db.query(ApifoxScript)
        .filter(ApifoxScript.project_id == project_id)
        .order_by(ApifoxScript.sort_order, ApifoxScript.id)
        .all()
    )


def get_script(db: Session, script_id: int) -> Optional[ApifoxScript]:
    return db.query(ApifoxScript).filter(ApifoxScript.id == script_id).first()


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj) -> None:
    db.delete(obj)


def count_script_refs(db: Session, script_id: int) -> int:
    # 用例与接口两处引用都算，避免删掉仍被引用的脚本
    case_refs = db.query(ApifoxCaseScript).filter(ApifoxCaseScript.script_id == script_id).count()
    endpoint_refs = (
        db.query(ApifoxEndpointScript).filter(ApifoxEndpointScript.script_id == script_id).count()
    )
    return case_refs + endpoint_refs


def list_case_scripts(db: Session, case_id: int) -> List[ApifoxCaseScript]:
    return (
        db.query(ApifoxCaseScript)
        .filter(ApifoxCaseScript.case_id == case_id)
        .order_by(ApifoxCaseScript.sort_order, ApifoxCaseScript.id)
        .all()
    )


def delete_case_scripts(db: Session, case_id: int, phase: str | None = None) -> None:
    query = db.query(ApifoxCaseScript).filter(ApifoxCaseScript.case_id == case_id)
    if phase is not None:
        query = query.filter(ApifoxCaseScript.phase == phase)
    query.delete(synchronize_session=False)


def list_endpoint_scripts(db: Session, endpoint_id: int) -> List[ApifoxEndpointScript]:
    return (
        db.query(ApifoxEndpointScript)
        .filter(ApifoxEndpointScript.endpoint_id == endpoint_id)
        .order_by(ApifoxEndpointScript.sort_order, ApifoxEndpointScript.id)
        .all()
    )


def delete_endpoint_scripts(db: Session, endpoint_id: int, phase: str | None = None) -> None:
    query = db.query(ApifoxEndpointScript).filter(ApifoxEndpointScript.endpoint_id == endpoint_id)
    if phase is not None:
        query = query.filter(ApifoxEndpointScript.phase == phase)
    query.delete(synchronize_session=False)

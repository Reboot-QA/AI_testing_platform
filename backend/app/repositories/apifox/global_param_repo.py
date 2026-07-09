"""Apifox 全局参数 · 数据访问层。不含业务校验；不提交事务。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.global_param import ApifoxGlobalParam


def list_params(db: Session, project_id: int) -> List[ApifoxGlobalParam]:
    return (
        db.query(ApifoxGlobalParam)
        .filter(ApifoxGlobalParam.project_id == project_id)
        .order_by(ApifoxGlobalParam.sort_order, ApifoxGlobalParam.id)
        .all()
    )


def get_param(db: Session, param_id: int) -> Optional[ApifoxGlobalParam]:
    return db.query(ApifoxGlobalParam).filter(ApifoxGlobalParam.id == param_id).first()


def add(db: Session, obj: ApifoxGlobalParam) -> ApifoxGlobalParam:
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj: ApifoxGlobalParam) -> None:
    db.delete(obj)

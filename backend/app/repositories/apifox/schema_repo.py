"""Apifox 数据模型(Schema) · 数据访问层。不含业务校验与权限；不提交事务（service commit）。"""

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.apifox.data_model import ApifoxSchema
from app.models.apifox.endpoint import ApifoxEndpoint


def count_endpoint_refs(db: Session, schema_id: int) -> int:
    """有多少接口把该数据模型绑为响应契约（删除前置校验）。"""
    return db.query(ApifoxEndpoint).filter(ApifoxEndpoint.response_schema_id == schema_id).count()


def list_schemas(db: Session, project_id: int) -> List[ApifoxSchema]:
    return (
        db.query(ApifoxSchema)
        .filter(ApifoxSchema.project_id == project_id)
        .order_by(ApifoxSchema.sort_order, ApifoxSchema.id)
        .all()
    )


def next_sort_order(db: Session, project_id: int) -> int:
    """项目内末尾的 sort_order + 1；空项目返回 0。新建时排到最后用。"""
    current_max = (
        db.query(func.max(ApifoxSchema.sort_order)).filter(ApifoxSchema.project_id == project_id).scalar()
    )
    return current_max + 1 if current_max is not None else 0


def get_schema(db: Session, schema_id: int) -> Optional[ApifoxSchema]:
    return db.query(ApifoxSchema).filter(ApifoxSchema.id == schema_id).first()


def get_schema_by_name(db: Session, project_id: int, name: str) -> Optional[ApifoxSchema]:
    return (
        db.query(ApifoxSchema)
        .filter(ApifoxSchema.project_id == project_id, ApifoxSchema.name == name)
        .first()
    )


def add(db: Session, obj: ApifoxSchema) -> ApifoxSchema:
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj: ApifoxSchema) -> None:
    db.delete(obj)

"""Apifox 数据模型(Schema) · 数据访问层。不含业务校验与权限；不提交事务（service commit）。"""

from typing import List, Optional

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


def get_schema(db: Session, schema_id: int) -> Optional[ApifoxSchema]:
    return db.query(ApifoxSchema).filter(ApifoxSchema.id == schema_id).first()


def add(db: Session, obj: ApifoxSchema) -> ApifoxSchema:
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj: ApifoxSchema) -> None:
    db.delete(obj)

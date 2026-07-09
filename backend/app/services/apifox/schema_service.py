"""Apifox 数据模型(Schema) · 业务层（唯一 name 校验 + json_schema 合法 JSON 校验）。

非法输入抛 ValueError（router 转 400）。写操作末尾 commit。权限在 router。
"""

import json
from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.data_model import ApifoxSchema
from app.repositories.apifox import schema_repo as repo
from app.routers.apifox.data_model_schemas import (
    SchemaBrief,
    SchemaCreate,
    SchemaOut,
    SchemaUpdate,
)


def _validate_json(text: str) -> None:
    try:
        json.loads(text)
    except (ValueError, TypeError):
        raise ValueError("json_schema 不是合法 JSON")


def _require_unique_name(db: Session, project_id: int, name: str, exclude_id: int | None = None) -> None:
    for s in repo.list_schemas(db, project_id):
        if s.name == name and s.id != exclude_id:
            raise ValueError("模型名已存在")


def _out(schema: ApifoxSchema) -> SchemaOut:
    return SchemaOut(
        id=schema.id,
        project_id=schema.project_id,
        name=schema.name,
        json_schema=schema.json_schema or "{}",
        description=schema.description,
        sort_order=schema.sort_order,
        created_at=schema.created_at,
        updated_at=schema.updated_at,
    )


def list_schemas(db: Session, project_id: int) -> List[SchemaBrief]:
    return [
        SchemaBrief(id=s.id, name=s.name, description=s.description, sort_order=s.sort_order)
        for s in repo.list_schemas(db, project_id)
    ]


def create_schema(db: Session, project_id: int, data: SchemaCreate) -> SchemaOut:
    _require_unique_name(db, project_id, data.name)
    _validate_json(data.json_schema)
    schema = ApifoxSchema(
        project_id=project_id,
        name=data.name,
        json_schema=data.json_schema,
        description=data.description,
    )
    repo.add(db, schema)
    db.commit()
    db.refresh(schema)
    return _out(schema)


def get_schema_out(schema: ApifoxSchema) -> SchemaOut:
    return _out(schema)


def update_schema(db: Session, schema: ApifoxSchema, data: SchemaUpdate) -> SchemaOut:
    if data.name is not None and data.name != schema.name:
        _require_unique_name(db, schema.project_id, data.name, exclude_id=schema.id)
        schema.name = data.name
    if data.json_schema is not None:
        _validate_json(data.json_schema)
        schema.json_schema = data.json_schema
    if "description" in data.model_fields_set:
        schema.description = data.description
    if data.sort_order is not None:
        schema.sort_order = data.sort_order
    db.commit()
    db.refresh(schema)
    return _out(schema)


def delete_schema(db: Session, schema: ApifoxSchema) -> None:
    repo.delete(db, schema)
    db.commit()

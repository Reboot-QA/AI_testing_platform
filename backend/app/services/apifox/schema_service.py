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
from app.services.apifox import schema_ref


def _validate_json(text: str) -> None:
    try:
        json.loads(text)
    except (ValueError, TypeError):
        raise ValueError("json_schema 不是合法 JSON")


def _require_unique_name(db: Session, project_id: int, name: str, exclude_id: int | None = None) -> None:
    for s in repo.list_schemas(db, project_id):
        if s.name == name and s.id != exclude_id:
            raise ValueError("模型名已存在")


def _count_model_refs(db: Session, project_id: int, schema_name: str) -> int:
    """项目内其他模型的 json_schema 通过 $ref 引用本模型名的个数。"""
    return sum(
        1
        for s in repo.list_schemas(db, project_id)
        if s.name != schema_name and schema_name in schema_ref.extract_model_refs(s.json_schema)
    )


def _ref_count(db: Session, schema: ApifoxSchema) -> int:
    """被引用总数 = 接口响应契约(按 id) + 其他模型 $ref(按名)。"""
    return repo.count_endpoint_refs(db, schema.id) + _count_model_refs(
        db, schema.project_id, schema.name
    )


def _would_cycle(db: Session, project_id: int, model_name: str, refs: set[str]) -> bool:
    """从 refs 出发沿引用图 DFS，能回到 model_name 即成环（含自引用）。"""
    stack = list(refs)
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current == model_name:
            return True
        if current in seen:
            continue
        seen.add(current)
        target = repo.get_schema_by_name(db, project_id, current)
        if target:
            stack.extend(schema_ref.extract_model_refs(target.json_schema))
    return False


def _validate_refs(db: Session, project_id: int, model_name: str, json_schema_text: str) -> None:
    refs = schema_ref.extract_model_refs(json_schema_text)
    for ref_name in refs:
        if ref_name == model_name:
            raise ValueError(f"数据模型不能引用自身：{ref_name}")
        if not repo.get_schema_by_name(db, project_id, ref_name):
            raise ValueError(f"引用的数据模型不存在：{ref_name}")
    if _would_cycle(db, project_id, model_name, refs):
        raise ValueError("数据模型引用形成循环，请调整引用关系")


def _out(db: Session, schema: ApifoxSchema) -> SchemaOut:
    return SchemaOut(
        id=schema.id,
        project_id=schema.project_id,
        name=schema.name,
        json_schema=schema.json_schema or "{}",
        description=schema.description,
        sort_order=schema.sort_order,
        created_at=schema.created_at,
        updated_at=schema.updated_at,
        resolved_schema=schema_ref.resolve_schema_text(db, schema.project_id, schema.json_schema),
    )


def list_schemas(db: Session, project_id: int) -> List[SchemaBrief]:
    return [
        SchemaBrief(
            id=s.id,
            name=s.name,
            description=s.description,
            sort_order=s.sort_order,
            ref_count=_ref_count(db, s),
        )
        for s in repo.list_schemas(db, project_id)
    ]


def create_schema(db: Session, project_id: int, data: SchemaCreate) -> SchemaOut:
    _require_unique_name(db, project_id, data.name)
    _validate_json(data.json_schema)
    _validate_refs(db, project_id, data.name, data.json_schema)
    schema = ApifoxSchema(
        project_id=project_id,
        name=data.name,
        json_schema=data.json_schema,
        description=data.description,
    )
    repo.add(db, schema)
    db.commit()
    db.refresh(schema)
    return _out(db, schema)


def get_schema_out(db: Session, schema: ApifoxSchema) -> SchemaOut:
    return _out(db, schema)


def update_schema(db: Session, schema: ApifoxSchema, data: SchemaUpdate) -> SchemaOut:
    if data.name is not None and data.name != schema.name:
        # 模型间按名引用，被引用时改名会断链——禁止（接口按 id 引用不受影响）
        model_refs = _count_model_refs(db, schema.project_id, schema.name)
        if model_refs:
            raise ValueError(f"数据模型被 {model_refs} 个模型引用，改名会断开引用，请先解除引用再改名")
        _require_unique_name(db, schema.project_id, data.name, exclude_id=schema.id)
        schema.name = data.name
    if data.json_schema is not None:
        _validate_json(data.json_schema)
        _validate_refs(db, schema.project_id, schema.name, data.json_schema)
        schema.json_schema = data.json_schema
    if "description" in data.model_fields_set:
        schema.description = data.description
    if data.sort_order is not None:
        schema.sort_order = data.sort_order
    db.commit()
    db.refresh(schema)
    return _out(db, schema)


def delete_schema(db: Session, schema: ApifoxSchema) -> None:
    endpoint_refs = repo.count_endpoint_refs(db, schema.id)
    if endpoint_refs:
        raise ValueError(f"数据模型被 {endpoint_refs} 个接口绑为响应契约，请先解除引用再删除")
    model_refs = _count_model_refs(db, schema.project_id, schema.name)
    if model_refs:
        raise ValueError(f"数据模型被 {model_refs} 个其他模型 $ref 引用，请先解除引用再删除")
    repo.delete(db, schema)
    db.commit()

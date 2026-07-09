"""Apifox 数据模型(Schema) · 路由（项目作用域，复用 project_access_service）。"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.data_model import ApifoxSchema
from app.models.user import User
from app.repositories.apifox import schema_repo as repo
from app.routers.apifox.data_model_schemas import (
    SchemaBrief,
    SchemaCreate,
    SchemaOut,
    SchemaUpdate,
)
from app.services.apifox import schema_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·数据模型"])


def _schema_checked(db: Session, sid: int, user: User) -> ApifoxSchema:
    schema = repo.get_schema(db, sid)
    if not schema:
        raise HTTPException(status_code=404, detail="数据模型不存在")
    get_accessible_project(db, schema.project_id, user)
    return schema


@router.get("/projects/{pid}/schemas", response_model=List[SchemaBrief])
def list_schemas(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_schemas(db, pid)


@router.post("/projects/{pid}/schemas", response_model=SchemaOut)
def create_schema(
    pid: int, data: SchemaCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_schema(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/schemas/{sid}", response_model=SchemaOut)
def get_schema(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    schema = _schema_checked(db, sid, user)
    return service.get_schema_out(schema)


@router.put("/schemas/{sid}", response_model=SchemaOut)
def update_schema(
    sid: int, data: SchemaUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    schema = _schema_checked(db, sid, user)
    try:
        return service.update_schema(db, schema, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/schemas/{sid}")
def delete_schema(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    schema = _schema_checked(db, sid, user)
    service.delete_schema(db, schema)
    return {"message": "数据模型已删除"}

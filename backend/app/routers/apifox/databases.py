"""Apifox 环境数据库连接 · 路由（环境作用域，经环境回溯项目做权限校验）。"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.database_conn import ApifoxEnvironmentDatabase
from app.models.user import User
from app.repositories.apifox import database_conn_repo as repo
from app.repositories.apifox import variable_repo
from app.routers.apifox.database_schemas import DatabaseCreate, DatabaseOut, DatabaseUpdate
from app.services.apifox import database_conn_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·数据库连接"])


def _env_checked(db: Session, eid: int, user: User) -> None:
    env = variable_repo.get_environment(db, eid)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    get_accessible_project(db, env.project_id, user)


def _conn_checked(db: Session, cid: int, user: User) -> ApifoxEnvironmentDatabase:
    conn = repo.get(db, cid)
    if not conn:
        raise HTTPException(status_code=404, detail="数据库连接不存在")
    _env_checked(db, conn.environment_id, user)
    return conn


@router.get("/environments/{eid}/databases", response_model=List[DatabaseOut])
def list_databases(eid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _env_checked(db, eid, user)
    return service.list_databases(db, eid)


@router.post("/environments/{eid}/databases", response_model=DatabaseOut)
def create_database(
    eid: int, data: DatabaseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _env_checked(db, eid, user)
    try:
        return service.create_database(db, eid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/env-databases/{cid}", response_model=DatabaseOut)
def update_database(
    cid: int, data: DatabaseUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    conn = _conn_checked(db, cid, user)
    try:
        return service.update_database(db, conn, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/env-databases/{cid}")
def delete_database(cid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conn = _conn_checked(db, cid, user)
    service.delete_database(db, conn)
    return {"message": "数据库连接已删除"}

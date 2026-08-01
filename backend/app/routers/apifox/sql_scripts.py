"""Apifox SQL 脚本库 · 路由（项目作用域，复用 project_access_service）。

/sql-scripts/debug 需排在 /sql-scripts/{sid} 之前，避免 "debug" 被当作 sid 命中动态路由。
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.sql_script import ApifoxSqlScript
from app.models.user import User
from app.repositories.apifox import database_conn_repo, variable_repo
from app.repositories.apifox import sql_script_repo as repo
from app.routers.apifox.sql_script_schemas import (
    SqlScriptBrief,
    SqlScriptCreate,
    SqlScriptDebugIn,
    SqlScriptDebugOut,
    SqlScriptOut,
    SqlScriptUpdate,
)
from app.services.apifox import sql_script_service as service
from app.services.apifox.errors import ConflictError
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·SQL脚本库"])


def _script_checked(db: Session, sid: int, user: User) -> ApifoxSqlScript:
    script = repo.get_script(db, sid)
    if not script:
        raise HTTPException(status_code=404, detail="SQL 脚本不存在")
    get_accessible_project(db, script.project_id, user)
    return script


@router.get("/projects/{pid}/sql-scripts", response_model=List[SqlScriptBrief])
def list_sql_scripts(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_scripts(db, pid)


@router.post("/projects/{pid}/sql-scripts", response_model=SqlScriptOut)
def create_sql_script(
    pid: int, data: SqlScriptCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_script(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/sql-scripts/debug", response_model=SqlScriptDebugOut)
def debug_sql_script(
    data: SqlScriptDebugIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """库内调试：选项目环境数据库连接执行 SQL，不落库、结果只预览。写操作由前端二次确认。"""
    conn = database_conn_repo.get(db, data.connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="数据库连接不存在")
    env = variable_repo.get_environment(db, conn.environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="连接所属环境不存在")
    get_accessible_project(db, env.project_id, user)  # 归属校验：无权限 403
    try:
        return service.debug_sql_script(conn, data.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/sql-scripts/{sid}", response_model=SqlScriptOut)
def get_sql_script(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    script = _script_checked(db, sid, user)
    return service.get_script_out(script)


@router.put("/sql-scripts/{sid}", response_model=SqlScriptOut)
def update_sql_script(
    sid: int, data: SqlScriptUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    script = _script_checked(db, sid, user)
    try:
        return service.update_script(db, script, data)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/sql-scripts/{sid}", status_code=204)
def delete_sql_script(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    script = _script_checked(db, sid, user)
    try:
        service.delete_script(db, script)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return None

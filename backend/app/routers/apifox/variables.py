"""Apifox 环境·变量 · 路由（项目作用域，复用 project_access_service 做归属+权限）。

与 endpoints.py 共用 /apifox 命名空间；本地值按当前登录用户操作。
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.variable import (
    ApifoxEnvironment,
    ApifoxEnvironmentServer,
    ApifoxEnvironmentVariable,
    ApifoxGlobalVariable,
)
from app.models.user import User
from app.repositories.apifox import variable_repo as repo
from app.routers.apifox.variable_schemas import (
    EnvironmentCreate,
    EnvironmentOut,
    EnvironmentUpdate,
    LocalValueSet,
    ServerCreate,
    ServerOut,
    ServerUpdate,
    VariableCreate,
    VariableOut,
    VariableUpdate,
)
from app.services.apifox import variable_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·环境变量"])


def _env_checked(db: Session, eid: int, user: User) -> ApifoxEnvironment:
    env = repo.get_environment(db, eid)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    get_accessible_project(db, env.project_id, user)
    return env


def _env_var_checked(db: Session, vid: int, user: User) -> ApifoxEnvironmentVariable:
    var = repo.get_env_var(db, vid)
    if not var:
        raise HTTPException(status_code=404, detail="变量不存在")
    env = repo.get_environment(db, var.environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    get_accessible_project(db, env.project_id, user)
    return var


def _global_var_checked(db: Session, gid: int, user: User) -> ApifoxGlobalVariable:
    var = repo.get_global_var(db, gid)
    if not var:
        raise HTTPException(status_code=404, detail="变量不存在")
    get_accessible_project(db, var.project_id, user)
    return var


def _server_checked(db: Session, sid: int, user: User) -> ApifoxEnvironmentServer:
    server = repo.get_server(db, sid)
    if not server:
        raise HTTPException(status_code=404, detail="前置 URL 不存在")
    env = repo.get_environment(db, server.environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    get_accessible_project(db, env.project_id, user)
    return server


# ---------- environments ----------
@router.get("/projects/{pid}/environments", response_model=List[EnvironmentOut])
def list_environments(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_environments(db, pid)


@router.post("/projects/{pid}/environments", response_model=EnvironmentOut)
def create_environment(
    pid: int, data: EnvironmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    return service.create_environment(db, pid, data)


@router.put("/environments/{eid}", response_model=EnvironmentOut)
def update_environment(
    eid: int, data: EnvironmentUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    env = _env_checked(db, eid, user)
    return service.update_environment(db, env, data)


@router.delete("/environments/{eid}")
def delete_environment(eid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    env = _env_checked(db, eid, user)
    service.delete_environment(db, env)
    return {"message": "环境已删除"}


# ---------- environment servers（命名前置 URL） ----------
@router.get("/environments/{eid}/servers", response_model=List[ServerOut])
def list_servers(eid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    env = _env_checked(db, eid, user)
    return service.list_servers(db, env.id)


@router.post("/environments/{eid}/servers", response_model=ServerOut)
def create_server(
    eid: int, data: ServerCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    env = _env_checked(db, eid, user)
    try:
        return service.create_server(db, env.id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/environment-servers/{sid}", response_model=ServerOut)
def update_server(
    sid: int, data: ServerUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    server = _server_checked(db, sid, user)
    try:
        return service.update_server(db, server, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/environment-servers/{sid}")
def delete_server(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    server = _server_checked(db, sid, user)
    service.delete_server(db, server)
    return {"message": "前置 URL 已删除"}


# ---------- 环境变量 ----------
@router.get("/environments/{eid}/variables", response_model=List[VariableOut])
def list_env_vars(eid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    env = _env_checked(db, eid, user)
    return service.list_env_vars(db, env.id, user.id)


@router.post("/environments/{eid}/variables", response_model=VariableOut)
def create_env_var(
    eid: int, data: VariableCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    env = _env_checked(db, eid, user)
    try:
        return service.create_env_var(db, env.id, data, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/env-variables/{vid}", response_model=VariableOut)
def update_env_var(
    vid: int, data: VariableUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    var = _env_var_checked(db, vid, user)
    try:
        return service.update_env_var(db, var, data, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/env-variables/{vid}")
def delete_env_var(vid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    var = _env_var_checked(db, vid, user)
    service.delete_env_var(db, var)
    return {"message": "变量已删除"}


@router.put("/env-variables/{vid}/local", response_model=VariableOut)
def set_env_local(
    vid: int, data: LocalValueSet, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    var = _env_var_checked(db, vid, user)
    return service.set_env_local(db, var, user.id, data.local_value)


# ---------- 全局变量 ----------
@router.get("/projects/{pid}/global-variables", response_model=List[VariableOut])
def list_global_vars(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_global_vars(db, pid, user.id)


@router.post("/projects/{pid}/global-variables", response_model=VariableOut)
def create_global_var(
    pid: int, data: VariableCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_global_var(db, pid, data, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/global-variables/{gid}", response_model=VariableOut)
def update_global_var(
    gid: int, data: VariableUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    var = _global_var_checked(db, gid, user)
    try:
        return service.update_global_var(db, var, data, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/global-variables/{gid}")
def delete_global_var(gid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    var = _global_var_checked(db, gid, user)
    service.delete_global_var(db, var)
    return {"message": "变量已删除"}


@router.put("/global-variables/{gid}/local", response_model=VariableOut)
def set_global_local(
    gid: int, data: LocalValueSet, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    var = _global_var_checked(db, gid, user)
    return service.set_global_local(db, var, user.id, data.local_value)

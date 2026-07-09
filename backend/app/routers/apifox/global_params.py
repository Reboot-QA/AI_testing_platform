"""Apifox 全局参数 · 路由（项目作用域，复用 project_access_service）。"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.global_param import ApifoxGlobalParam
from app.models.user import User
from app.repositories.apifox import global_param_repo as repo
from app.routers.apifox.global_param_schemas import (
    GlobalParamCreate,
    GlobalParamOut,
    GlobalParamUpdate,
)
from app.services.apifox import global_param_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·全局参数"])


def _param_checked(db: Session, gid: int, user: User) -> ApifoxGlobalParam:
    param = repo.get_param(db, gid)
    if not param:
        raise HTTPException(status_code=404, detail="全局参数不存在")
    get_accessible_project(db, param.project_id, user)
    return param


@router.get("/projects/{pid}/global-params", response_model=List[GlobalParamOut])
def list_params(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_params(db, pid)


@router.post("/projects/{pid}/global-params", response_model=GlobalParamOut)
def create_param(
    pid: int, data: GlobalParamCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_param(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/global-params/{gid}", response_model=GlobalParamOut)
def update_param(
    gid: int, data: GlobalParamUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    param = _param_checked(db, gid, user)
    try:
        return service.update_param(db, param, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/global-params/{gid}")
def delete_param(gid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    param = _param_checked(db, gid, user)
    service.delete_param(db, param)
    return {"message": "全局参数已删除"}

"""Apifox 接口管理 · 路由（项目作用域，复用 project_access_service 做归属+权限）。

命名空间 /apifox，与旧 /api-automation 并存不撞。router 只做参数校验/权限编排，业务在 service。
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.endpoint import ApifoxEndpoint, ApifoxFolder
from app.models.user import User
from app.repositories.apifox import endpoint_repo as repo
from app.routers.apifox.schemas import (
    EndpointBrief,
    EndpointCreate,
    EndpointOut,
    EndpointUpdate,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    TreeReorderRequest,
)
from app.services.apifox import endpoint_service as service
from app.services.apifox.errors import ConflictError
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2"])


def _folder_checked(db: Session, folder_id: int, user: User) -> ApifoxFolder:
    folder = repo.get_folder(db, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="文件夹不存在")
    get_accessible_project(db, folder.project_id, user)  # 无权限抛 404
    return folder


def _endpoint_checked(db: Session, endpoint_id: int, user: User) -> ApifoxEndpoint:
    endpoint = repo.get_endpoint(db, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="接口不存在")
    get_accessible_project(db, endpoint.project_id, user)
    return endpoint


# ---------- folders ----------
@router.get("/projects/{pid}/folders", response_model=List[FolderOut])
def list_folders(
    pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    return service.list_folders(db, pid)


@router.post("/projects/{pid}/folders", response_model=FolderOut)
def create_folder(
    pid: int,
    data: FolderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_folder(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/folders/{fid}", response_model=FolderOut)
def update_folder(
    fid: int,
    data: FolderUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    folder = _folder_checked(db, fid, user)
    try:
        return service.update_folder(db, folder, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/folders/{fid}")
def delete_folder(
    fid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    folder = _folder_checked(db, fid, user)
    try:
        service.delete_folder(db, folder)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "文件夹已删除"}


# ---------- endpoints ----------
@router.get("/projects/{pid}/endpoints", response_model=List[EndpointBrief])
def list_endpoints(
    pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    return service.list_endpoints(db, pid)


@router.post("/projects/{pid}/endpoints", response_model=EndpointOut)
def create_endpoint(
    pid: int,
    data: EndpointCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_endpoint(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/endpoints/{eid}", response_model=EndpointOut)
def get_endpoint(
    eid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    endpoint = _endpoint_checked(db, eid, user)
    return service.get_endpoint_out(db, endpoint)


@router.put("/endpoints/{eid}", response_model=EndpointOut)
def update_endpoint(
    eid: int,
    data: EndpointUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    endpoint = _endpoint_checked(db, eid, user)
    try:
        return service.update_endpoint(db, endpoint, data)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/endpoints/{eid}")
def delete_endpoint(
    eid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    endpoint = _endpoint_checked(db, eid, user)
    service.delete_endpoint(db, endpoint)
    return {"message": "接口已删除"}


# ---------- 树拖拽重排 ----------
@router.post("/projects/{pid}/tree/reorder")
def reorder_tree(
    pid: int,
    data: TreeReorderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    try:
        service.reorder_tree(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "已保存排序"}

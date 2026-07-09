"""Apifox 接口管理 · 业务层（校验归属 + 编排 repository + request_spec JSON 序列化）。

归属：folder/endpoint 必须属于已通过 project_access 校验的 project；跨项目引用抛 ValueError（router 转 400）。
不做权限判定（在 router 用 project_access_service）。提交事务由本层负责（写操作末尾 commit）。
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxEndpoint, ApifoxFolder
from app.repositories.apifox import endpoint_repo as repo
from app.routers.apifox.schemas import (
    EndpointBrief,
    EndpointCreate,
    EndpointOut,
    EndpointUpdate,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    RequestSpec,
)


def _load_spec(text: str | None) -> RequestSpec:
    if not text:
        return RequestSpec()
    try:
        return RequestSpec.model_validate_json(text)
    except ValueError:
        return RequestSpec()


def _folder_out(folder: ApifoxFolder) -> FolderOut:
    return FolderOut(
        id=folder.id,
        project_id=folder.project_id,
        parent_id=folder.parent_id,
        name=folder.name,
        sort_order=folder.sort_order,
    )


def _endpoint_out(endpoint: ApifoxEndpoint) -> EndpointOut:
    return EndpointOut(
        id=endpoint.id,
        project_id=endpoint.project_id,
        folder_id=endpoint.folder_id,
        name=endpoint.name,
        method=endpoint.method,
        path=endpoint.path,
        request_spec=_load_spec(endpoint.request_spec),
        description=endpoint.description,
        sort_order=endpoint.sort_order,
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
    )


def _require_folder_in_project(db: Session, folder_id: int | None, project_id: int) -> None:
    if folder_id is None:
        return
    folder = repo.get_folder(db, folder_id)
    if not folder or folder.project_id != project_id:
        raise ValueError("所选文件夹不存在或不属于该项目")


# ---------- folders ----------
def list_folders(db: Session, project_id: int) -> List[FolderOut]:
    return [_folder_out(f) for f in repo.list_folders(db, project_id)]


def create_folder(db: Session, project_id: int, data: FolderCreate) -> FolderOut:
    _require_folder_in_project(db, data.parent_id, project_id)
    folder = ApifoxFolder(project_id=project_id, parent_id=data.parent_id, name=data.name)
    repo.create_folder(db, folder)
    db.commit()
    db.refresh(folder)
    return _folder_out(folder)


def update_folder(db: Session, folder: ApifoxFolder, data: FolderUpdate) -> FolderOut:
    if "parent_id" in data.model_fields_set:
        if data.parent_id == folder.id:
            raise ValueError("文件夹不能移动到自身")
        _require_folder_in_project(db, data.parent_id, folder.project_id)
        folder.parent_id = data.parent_id
    if data.name is not None:
        folder.name = data.name
    if data.sort_order is not None:
        folder.sort_order = data.sort_order
    db.commit()
    db.refresh(folder)
    return _folder_out(folder)


def delete_folder(db: Session, folder: ApifoxFolder) -> None:
    if repo.count_child_folders(db, folder.id) or repo.count_folder_endpoints(db, folder.id):
        raise ValueError("文件夹非空，请先删除其下的接口与子文件夹")
    repo.delete_folder(db, folder)
    db.commit()


# ---------- endpoints ----------
def list_endpoints(db: Session, project_id: int) -> List[EndpointBrief]:
    return [
        EndpointBrief(
            id=e.id,
            folder_id=e.folder_id,
            name=e.name,
            method=e.method,
            path=e.path,
            sort_order=e.sort_order,
        )
        for e in repo.list_endpoints(db, project_id)
    ]


def create_endpoint(db: Session, project_id: int, data: EndpointCreate) -> EndpointOut:
    _require_folder_in_project(db, data.folder_id, project_id)
    endpoint = ApifoxEndpoint(
        project_id=project_id,
        folder_id=data.folder_id,
        name=data.name,
        method=data.method,
        path=data.path,
        request_spec=data.request_spec.model_dump_json(),
        description=data.description,
    )
    repo.create_endpoint(db, endpoint)
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint)


def get_endpoint_out(endpoint: ApifoxEndpoint) -> EndpointOut:
    return _endpoint_out(endpoint)


def update_endpoint(db: Session, endpoint: ApifoxEndpoint, data: EndpointUpdate) -> EndpointOut:
    if "folder_id" in data.model_fields_set:
        _require_folder_in_project(db, data.folder_id, endpoint.project_id)
        endpoint.folder_id = data.folder_id
    if data.name is not None:
        endpoint.name = data.name
    if data.method is not None:
        endpoint.method = data.method
    if data.path is not None:
        endpoint.path = data.path
    if data.request_spec is not None:
        endpoint.request_spec = data.request_spec.model_dump_json()
    if data.description is not None:
        endpoint.description = data.description
    if data.sort_order is not None:
        endpoint.sort_order = data.sort_order
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(endpoint)


def delete_endpoint(db: Session, endpoint: ApifoxEndpoint) -> None:
    repo.delete_endpoint(db, endpoint)
    db.commit()

"""Apifox 全局参数 · 业务层（唯一 (location,key)、location 校验）。

非法输入抛 ValueError（router 转 400）。写操作末尾 commit。自动附加逻辑留 P4。
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.global_param import ApifoxGlobalParam
from app.repositories.apifox import global_param_repo as repo
from app.routers.apifox.global_param_schemas import (
    GlobalParamCreate,
    GlobalParamOut,
    GlobalParamUpdate,
)

VALID_LOCATIONS = {"header", "query", "cookie", "body"}


def _validate_location(location: str) -> None:
    if location not in VALID_LOCATIONS:
        raise ValueError("无效的参数位置")


def _require_unique(
    db: Session, project_id: int, location: str, key: str, exclude_id: int | None = None
) -> None:
    for p in repo.list_params(db, project_id):
        if p.location == location and p.key == key and p.id != exclude_id:
            raise ValueError("同位置下参数名已存在")


def _out(param: ApifoxGlobalParam) -> GlobalParamOut:
    return GlobalParamOut(
        id=param.id,
        project_id=param.project_id,
        location=param.location,
        key=param.key,
        value=param.value,
        enabled=param.enabled,
        sort_order=param.sort_order,
    )


def list_params(db: Session, project_id: int) -> List[GlobalParamOut]:
    return [_out(p) for p in repo.list_params(db, project_id)]


def create_param(db: Session, project_id: int, data: GlobalParamCreate) -> GlobalParamOut:
    _validate_location(data.location)
    _require_unique(db, project_id, data.location, data.key)
    param = ApifoxGlobalParam(
        project_id=project_id,
        location=data.location,
        key=data.key,
        value=data.value,
        enabled=data.enabled,
    )
    repo.add(db, param)
    db.commit()
    db.refresh(param)
    return _out(param)


def update_param(db: Session, param: ApifoxGlobalParam, data: GlobalParamUpdate) -> GlobalParamOut:
    location = data.location if data.location is not None else param.location
    key = data.key if data.key is not None else param.key
    if data.location is not None:
        _validate_location(data.location)
    if location != param.location or key != param.key:
        _require_unique(db, param.project_id, location, key, exclude_id=param.id)
    param.location = location
    param.key = key
    if "value" in data.model_fields_set:
        param.value = data.value
    if data.enabled is not None:
        param.enabled = data.enabled
    if data.sort_order is not None:
        param.sort_order = data.sort_order
    db.commit()
    db.refresh(param)
    return _out(param)


def delete_param(db: Session, param: ApifoxGlobalParam) -> None:
    repo.delete(db, param)
    db.commit()

"""Apifox 项目级数据集 · 路由（项目作用域，复用 project_access_service）。"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.dataset import ApifoxDataset
from app.models.user import User
from app.repositories.apifox import dataset_repo as repo
from app.routers.apifox.dataset_schemas import (
    DatasetBrief,
    DatasetCreate,
    DatasetOut,
    DatasetUpdate,
)
from app.services.apifox import dataset_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·数据集"])


def _dataset_checked(db: Session, did: int, user: User) -> ApifoxDataset:
    dataset = repo.get_dataset(db, did)
    if not dataset:
        raise HTTPException(status_code=404, detail="数据集不存在")
    get_accessible_project(db, dataset.project_id, user)
    return dataset


@router.get("/projects/{pid}/datasets", response_model=List[DatasetBrief])
def list_datasets(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_datasets(db, pid)


@router.post("/projects/{pid}/datasets", response_model=DatasetOut)
def create_dataset(
    pid: int, data: DatasetCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_dataset(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/datasets/{did}", response_model=DatasetOut)
def get_dataset(did: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dataset = _dataset_checked(db, did, user)
    return service.get_dataset_out(db, dataset)


@router.put("/datasets/{did}", response_model=DatasetOut)
def update_dataset(
    did: int, data: DatasetUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    dataset = _dataset_checked(db, did, user)
    try:
        return service.update_dataset(db, dataset, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/datasets/{did}")
def delete_dataset(did: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    dataset = _dataset_checked(db, did, user)
    try:
        service.delete_dataset(db, dataset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "数据集已删除"}

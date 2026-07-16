"""Apifox 场景编排 · 路由（项目作用域，复用 project_access_service）。"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.endpoint import ApifoxFolder
from app.models.apifox.scenario import ApifoxScenario
from app.models.user import User
from app.repositories.apifox import scenario_repo as repo
from app.routers.apifox.scenario_schemas import (
    ScenarioBrief,
    ScenarioCreate,
    ScenarioFolderCreate,
    ScenarioFolderOut,
    ScenarioFolderUpdate,
    ScenarioOut,
    ScenarioUpdate,
)
from app.services.apifox import scenario_folder_service as folder_service
from app.services.apifox import scenario_service as service
from app.services.apifox.errors import ConflictError
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·场景"])


def _scenario_checked(db: Session, sid: int, user: User) -> ApifoxScenario:
    scenario = repo.get_scenario(db, sid)
    if not scenario:
        raise HTTPException(status_code=404, detail="场景不存在")
    get_accessible_project(db, scenario.project_id, user)
    return scenario


def _scenario_folder_checked(db: Session, fid: int, user: User) -> ApifoxFolder:
    folder = repo.get_scenario_folder(db, fid)
    if not folder:
        raise HTTPException(status_code=404, detail="场景文件夹不存在")
    get_accessible_project(db, folder.project_id, user)
    return folder


@router.get("/projects/{pid}/scenario-folders", response_model=List[ScenarioFolderOut])
def list_scenario_folders(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return folder_service.list_folders(db, pid)


@router.post("/projects/{pid}/scenario-folders", response_model=ScenarioFolderOut)
def create_scenario_folder(
    pid: int, data: ScenarioFolderCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    return folder_service.create_folder(db, pid, data.name)


@router.put("/scenario-folders/{fid}", response_model=ScenarioFolderOut)
def rename_scenario_folder(
    fid: int, data: ScenarioFolderUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    folder = _scenario_folder_checked(db, fid, user)
    return folder_service.rename_folder(db, folder, data.name)


@router.delete("/scenario-folders/{fid}")
def delete_scenario_folder(fid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    folder = _scenario_folder_checked(db, fid, user)
    folder_service.delete_folder(db, folder)
    return {"message": "已删除"}


@router.get("/projects/{pid}/scenarios", response_model=List[ScenarioBrief])
def list_scenarios(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return service.list_scenarios(db, pid)


@router.post("/projects/{pid}/scenarios", response_model=ScenarioOut)
def create_scenario(
    pid: int, data: ScenarioCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_accessible_project(db, pid, user)
    try:
        return service.create_scenario(db, pid, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/scenarios/{sid}", response_model=ScenarioOut)
def get_scenario(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scenario = _scenario_checked(db, sid, user)
    return service.get_scenario_out(db, scenario)


@router.put("/scenarios/{sid}", response_model=ScenarioOut)
def update_scenario(
    sid: int, data: ScenarioUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    scenario = _scenario_checked(db, sid, user)
    try:
        return service.update_scenario(db, scenario, data)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=exc.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/scenarios/{sid}")
def delete_scenario(sid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scenario = _scenario_checked(db, sid, user)
    try:
        service.delete_scenario(db, scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "场景已删除"}

"""Apifox 回收站 · 路由（项目作用域，软删除的场景/套件/用例统一列出 / 还原 / 彻底删）。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.routers.apifox.trash_schemas import TrashBatchIn, TrashBatchOut, TrashKind, TrashPageOut
from app.services.apifox import trash_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·回收站"])


@router.get("/projects/{pid}/trash", response_model=TrashPageOut)
def list_trash(
    pid: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None, max_length=200),
    kind: Optional[TrashKind] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    return service.list_trash_page(db, pid, page, page_size, keyword, kind)


@router.post("/projects/{pid}/trash/batch-restore", response_model=TrashBatchOut)
def batch_restore_trash(
    pid: int,
    data: TrashBatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    if not data.items:
        raise HTTPException(status_code=400, detail="请选择至少一项")
    return service.batch_restore(db, pid, data.items)


@router.post("/projects/{pid}/trash/batch-purge", response_model=TrashBatchOut)
def batch_purge_trash(
    pid: int,
    data: TrashBatchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    if not data.items:
        raise HTTPException(status_code=400, detail="请选择至少一项")
    return service.batch_purge(db, pid, data.items)


@router.post("/trash/{kind}/{item_id}/restore")
def restore_item(
    kind: str, item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project_id = _project_id_for(db, kind, item_id, user)
    try:
        obj = service._get_deleted(db, project_id, kind, item_id)
        service._restore_one(db, obj, kind)
    except LookupError:
        raise HTTPException(status_code=404, detail="回收站中无此项") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "已还原"}


@router.delete("/trash/{kind}/{item_id}")
def purge_item(
    kind: str, item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    project_id = _project_id_for(db, kind, item_id, user)
    try:
        obj = service._get_deleted(db, project_id, kind, item_id)
        service._purge_one(db, obj, kind)
    except LookupError:
        raise HTTPException(status_code=404, detail="回收站中无此项") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "已彻底删除"}


def _project_id_for(db: Session, kind: str, item_id: int, user: User) -> int:
    from app.repositories.apifox import case_repo, endpoint_repo, scenario_repo, suite_repo

    if kind == "scenario":
        obj = scenario_repo.get_scenario(db, item_id)
    elif kind == "suite":
        obj = suite_repo.get_suite(db, item_id)
    elif kind == "case":
        obj = case_repo.get_case(db, item_id)
    elif kind == "endpoint":
        obj = endpoint_repo.get_endpoint(db, item_id)
    else:
        raise HTTPException(status_code=400, detail="未知回收站类型")
    if not obj:
        raise HTTPException(status_code=404, detail="回收站中无此项")
    get_accessible_project(db, obj.project_id, user)
    return obj.project_id

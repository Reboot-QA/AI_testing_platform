"""Apifox · OpenAPI 导入 / 更新同步路由（项目作用域）。"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.routers.apifox.schemas import ImportDiffOut, ImportSyncReport
from app.services.apifox import import_service, import_sync_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·导入"])
logger = logging.getLogger(__name__)

# 外部 OpenAPI 文档结构不可控：解析畸形字段的结构性异常兜底为 422（含诊断），避免裸 500
_DOC_STRUCTURE_ERRORS = (KeyError, TypeError, AttributeError, IndexError)


def _doc_error(pid: int, action: str, exc: Exception) -> HTTPException:
    logger.exception("OpenAPI %s 解析失败 pid=%s", action, pid)
    return HTTPException(status_code=422, detail=f"OpenAPI 文档解析失败：{type(exc).__name__}: {exc}")


class ImportRequest(BaseModel):
    url: Optional[str] = None
    content: Optional[str] = None


class ImportSyncRequest(ImportRequest):
    # 更新同步时，是否删除「新 Swagger 已移除且无用例引用」的接口
    delete_unreferenced: bool = False


class ImportReport(BaseModel):
    total: int
    created: int
    skipped: int
    folders_created: int
    schemas_created: int = 0


def _load_doc(data: ImportRequest) -> Dict[str, Any]:
    if data.url and data.url.strip():
        return import_service.fetch_openapi(data.url.strip())
    if data.content and data.content.strip():
        return import_service.parse_content(data.content)
    raise ValueError("请提供 OpenAPI 的 URL 或粘贴 JSON 内容")


@router.post("/projects/{pid}/import/openapi", response_model=ImportReport)
def import_openapi(
    pid: int,
    data: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    try:
        report = import_service.import_openapi(db, pid, _load_doc(data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except _DOC_STRUCTURE_ERRORS as exc:
        db.rollback()
        raise _doc_error(pid, "导入", exc)
    return ImportReport(**report)


@router.post("/projects/{pid}/import/openapi/diff", response_model=ImportDiffOut)
def import_openapi_diff(
    pid: int,
    data: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新同步前的只读预览：新增/变更/移除 + 引用告警。"""
    get_accessible_project(db, pid, user)
    try:
        return import_sync_service.compute_diff(db, pid, _load_doc(data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except _DOC_STRUCTURE_ERRORS as exc:
        raise _doc_error(pid, "更新预览", exc)


@router.post("/projects/{pid}/import/openapi/sync", response_model=ImportSyncReport)
def import_openapi_sync(
    pid: int,
    data: ImportSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """应用更新同步：建新增、更新变更契约、按需删无引用移除项；有引用只告警。"""
    get_accessible_project(db, pid, user)
    try:
        return import_sync_service.apply_sync(db, pid, _load_doc(data), data.delete_unreferenced)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except _DOC_STRUCTURE_ERRORS as exc:
        db.rollback()
        raise _doc_error(pid, "更新同步", exc)

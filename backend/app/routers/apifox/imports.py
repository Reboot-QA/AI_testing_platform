"""Apifox · OpenAPI 导入 / 更新同步路由（项目作用域）。"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.routers.apifox.schemas import ImportDiffOut, ImportPreviewOut, ImportSyncReport
from app.services.apifox import (
    export_docs,
    export_postman,
    export_service,
    import_converters,
    import_service,
    import_sync_service,
)
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·导入"])
logger = logging.getLogger(__name__)

# 外部 OpenAPI 文档结构不可控：解析畸形字段的结构性异常兜底为 422（含诊断），避免裸 500
_DOC_STRUCTURE_ERRORS = (KeyError, TypeError, AttributeError, IndexError)


def _doc_error(pid: int, action: str, exc: Exception) -> HTTPException:
    logger.exception("OpenAPI %s 解析失败 pid=%s", action, pid)
    return HTTPException(status_code=422, detail=f"OpenAPI 文档解析失败：{type(exc).__name__}: {exc}")


class BasicAuth(BaseModel):
    username: str = ""
    password: str = ""


class ImportRequest(BaseModel):
    url: Optional[str] = None
    content: Optional[str] = None
    # URL 导入时的 Basic Auth（可选）；用户名为空视为不带认证
    basic_auth: Optional[BasicAuth] = None
    # Git 私有仓库 raw 文件导入的 Personal Access Token（可选）
    git_token: Optional[str] = None


class ImportSyncRequest(ImportRequest):
    # 更新同步时，是否删除「新 Swagger 已移除且无用例引用」的接口
    delete_unreferenced: bool = False


class ImportOpenapiRequest(ImportRequest):
    """执行导入时附带用户在「预览 & 配置」里的选择。"""

    # 导入位置：None = 根目录；文档 tag 作为其下的子目录
    target_folder_id: Optional[int] = None
    # 勾选的接口 key（形如 "GET /users"）；None = 不筛选，全部导入
    selected_keys: Optional[list[str]] = None
    # 已存在同 (method, path) 接口时：skip 跳过 / overwrite 覆盖请求契约
    on_conflict: str = "skip"
    # 是否一并导入 components/schemas 为数据模型
    with_schemas: bool = True


class ImportReport(BaseModel):
    total: int
    created: int
    updated: int = 0
    skipped: int
    folders_created: int
    schemas_created: int = 0


class ImportSourceOut(BaseModel):
    # 上次 URL 导入的地址（前端回填 + 同源识别为更新）；文件/cURL 导入不记
    url: Optional[str] = None


def _remember_import_url(db: Session, pid: int, url: Optional[str]) -> None:
    """URL 导入/更新成功后记住地址，供下次同源识别与回填。"""
    if url and url.strip():
        db.query(Project).filter(Project.id == pid).update(
            {Project.last_import_url: url.strip()}, synchronize_session=False
        )
        db.commit()


@router.get("/projects/{pid}/import-source", response_model=ImportSourceOut)
def get_import_source(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    proj = db.query(Project).filter(Project.id == pid).first()
    return ImportSourceOut(url=proj.last_import_url if proj else None)


def _csv(s: str) -> list:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


@router.get("/projects/{pid}/export/openapi")
def export_openapi(
    pid: int,
    spec_version: str = Query("3.0", description="3.0 | 3.1 | swagger2"),
    file_format: str = Query("json", description="json | yaml"),
    scope: str = Query("all", description="all | tags | endpoints"),
    tags: str = Query("", description="scope=tags 时逗号分隔的标签（文件夹名）"),
    exclude_tags: str = Query("", description="逗号分隔，排除这些标签"),
    endpoint_ids: str = Query("", description="scope=endpoints 时逗号分隔的接口 id"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出：按范围/标签过滤，按版本(3.0/3.1/Swagger2.0)与格式(JSON/YAML)生成，前端下载。"""
    get_accessible_project(db, pid, user)
    opts = export_service.ExportOptions(
        spec_version=spec_version,
        file_format=file_format,
        scope=scope,
        tags=_csv(tags),
        exclude_tags=_csv(exclude_tags),
        endpoint_ids=[int(x) for x in _csv(endpoint_ids) if x.isdigit()],
    )
    content, media_type, filename = export_service.export(db, pid, opts)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _scope_opts(scope: str, tags: str, exclude_tags: str, endpoint_ids: str) -> "export_service.ExportOptions":
    return export_service.ExportOptions(
        scope=scope,
        tags=_csv(tags),
        exclude_tags=_csv(exclude_tags),
        endpoint_ids=[int(x) for x in _csv(endpoint_ids) if x.isdigit()],
    )


@router.get("/projects/{pid}/export/postman")
def export_postman_endpoint(
    pid: int,
    scope: str = Query("all", description="all | tags | endpoints"),
    tags: str = Query(""),
    exclude_tags: str = Query(""),
    endpoint_ids: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出为 Postman Collection v2.1（按范围/标签过滤）。"""
    get_accessible_project(db, pid, user)
    opts = _scope_opts(scope, tags, exclude_tags, endpoint_ids)
    content, media_type, filename = export_postman.export_postman(db, pid, opts)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projects/{pid}/export/doc")
def export_doc_endpoint(
    pid: int,
    doc_format: str = Query("html", description="html | markdown | word"),
    scope: str = Query("all", description="all | tags | endpoints"),
    tags: str = Query(""),
    exclude_tags: str = Query(""),
    endpoint_ids: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导出接口文档：HTML / Markdown / Word。"""
    get_accessible_project(db, pid, user)
    opts = _scope_opts(scope, tags, exclude_tags, endpoint_ids)
    content, media_type, filename = export_docs.export_doc(db, pid, doc_format, opts)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _load_doc(data: ImportRequest) -> Dict[str, Any]:
    """拉取/取原始内容 → 归一化为 OpenAPI 3.x（支持 OpenAPI/Swagger/Postman/cURL）。"""
    if data.url and data.url.strip():
        auth = None
        if data.basic_auth and data.basic_auth.username:
            auth = (data.basic_auth.username, data.basic_auth.password)
        headers = import_service.git_token_headers(data.git_token.strip()) if data.git_token and data.git_token.strip() else None
        raw = import_service.fetch_source(data.url.strip(), auth=auth, headers=headers)
    elif data.content and data.content.strip():
        raw = data.content
    else:
        raise ValueError("请提供 URL 或粘贴内容（OpenAPI/Swagger/Postman/cURL）")
    return import_converters.to_openapi3(raw)


@router.post("/projects/{pid}/import/openapi/preview", response_model=ImportPreviewOut)
def import_openapi_preview(
    pid: int,
    data: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """导入前的只读预览：按 tag 分组列出待导入接口，标注已存在/契约有变更，供用户勾选。"""
    get_accessible_project(db, pid, user)
    try:
        return ImportPreviewOut(**import_service.preview_openapi(db, pid, _load_doc(data)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except _DOC_STRUCTURE_ERRORS as exc:
        raise _doc_error(pid, "导入预览", exc)


@router.post("/projects/{pid}/import/openapi", response_model=ImportReport)
def import_openapi(
    pid: int,
    data: ImportOpenapiRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    options = import_service.ImportOptions(
        target_folder_id=data.target_folder_id,
        selected_keys=set(data.selected_keys) if data.selected_keys is not None else None,
        on_conflict=data.on_conflict,
        with_schemas=data.with_schemas,
    )
    try:
        report = import_service.import_openapi(db, pid, _load_doc(data), options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        db.rollback()
        logger.exception("OpenAPI 导入唯一约束冲突 pid=%s", pid)
        raise HTTPException(status_code=409, detail="导入的接口或数据模型存在重名，请检查后重试")
    except _DOC_STRUCTURE_ERRORS as exc:
        db.rollback()
        raise _doc_error(pid, "导入", exc)
    _remember_import_url(db, pid, data.url)
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
        report = import_sync_service.apply_sync(db, pid, _load_doc(data), data.delete_unreferenced)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        db.rollback()
        logger.exception("OpenAPI 更新同步唯一约束冲突 pid=%s", pid)
        raise HTTPException(status_code=409, detail="导入的接口或数据模型存在重名，请检查后重试")
    except _DOC_STRUCTURE_ERRORS as exc:
        db.rollback()
        raise _doc_error(pid, "更新同步", exc)
    _remember_import_url(db, pid, data.url)
    return report

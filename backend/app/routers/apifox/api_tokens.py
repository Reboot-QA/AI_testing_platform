"""Apifox 项目级 API Token · 路由。

两类端点：
1) Token 管理（JWT 鉴权）：项目作用域列出 / 新建 / 吊销。
2) 通过 API 导入/导出（X-API-Token 头鉴权，无需 JWT）：token 即锁定项目，供外部系统调用。
"""

from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.apifox.api_token import ApifoxApiToken
from app.models.user import User
from app.routers.apifox.api_token_schemas import ApiTokenCreate, ApiTokenOut
from app.routers.apifox.imports import ImportRequest, _csv, _load_doc
from app.services.apifox import api_token_service, export_service, import_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·API Token"])
# 通过 API 导入/导出：X-API-Token 自鉴权、不需要 JWT，单独一个路由，
# 避免被 main.py 挂在 token 管理路由上的菜单权限依赖（要 JWT）误拦。
public_router = APIRouter(prefix="/apifox", tags=["接口自动化v2·API Token"])

# 外部 OpenAPI 文档结构不可控：解析畸形字段兜底为 422，避免裸 500
_DOC_STRUCTURE_ERRORS = (KeyError, TypeError, AttributeError, IndexError)


def _out(t: ApifoxApiToken) -> ApiTokenOut:
    return ApiTokenOut(
        id=t.id,
        project_id=t.project_id,
        name=t.name,
        token=t.token,
        last_used_at=t.last_used_at,
        created_at=t.created_at,
    )


# ---------- Token 管理（JWT） ----------
@router.get("/projects/{pid}/api-tokens", response_model=List[ApiTokenOut])
def list_api_tokens(pid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_accessible_project(db, pid, user)
    return [_out(t) for t in api_token_service.list_tokens(db, pid)]


@router.post("/projects/{pid}/api-tokens", response_model=ApiTokenOut)
def create_api_token(
    pid: int,
    data: ApiTokenCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    return _out(api_token_service.create_token(db, pid, data.name, user.id))


@router.delete("/api-tokens/{tid}", status_code=204)
def revoke_api_token(tid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    token = db.query(ApifoxApiToken).filter(ApifoxApiToken.id == tid).first()
    if not token:
        raise HTTPException(status_code=404, detail="API Token 不存在")
    get_accessible_project(db, token.project_id, user)
    api_token_service.revoke_token(db, token)
    return None


# ---------- 通过 API 导入/导出（X-API-Token） ----------
def _token_project(
    x_api_token: str = Header(..., alias="X-API-Token", description="项目 API Token"),
    db: Session = Depends(get_db),
) -> ApifoxApiToken:
    row = api_token_service.resolve_token(db, x_api_token)
    if not row:
        raise HTTPException(status_code=401, detail="无效或已吊销的 API Token")
    return row


@public_router.post("/api/import")
def import_via_token(
    data: ImportRequest,
    token: ApifoxApiToken = Depends(_token_project),
    db: Session = Depends(get_db),
):
    """外部系统凭 Token 导入到该 Token 所属项目。"""
    try:
        report = import_service.import_openapi(db, token.project_id, _load_doc(data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except _DOC_STRUCTURE_ERRORS as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"OpenAPI 文档解析失败：{type(exc).__name__}: {exc}")
    return report


@public_router.get("/api/export/openapi")
def export_via_token(
    spec_version: str = Query("3.0", description="3.0 | 3.1 | swagger2"),
    file_format: str = Query("json", description="json | yaml"),
    scope: str = Query("all", description="all | tags | endpoints"),
    tags: str = Query(""),
    exclude_tags: str = Query(""),
    endpoint_ids: str = Query(""),
    token: ApifoxApiToken = Depends(_token_project),
    db: Session = Depends(get_db),
):
    """外部系统凭 Token 导出该 Token 所属项目。"""
    opts = export_service.ExportOptions(
        spec_version=spec_version,
        file_format=file_format,
        scope=scope,
        tags=_csv(tags),
        exclude_tags=_csv(exclude_tags),
        endpoint_ids=[int(x) for x in _csv(endpoint_ids) if x.isdigit()],
    )
    content, media_type, filename = export_service.export(db, token.project_id, opts)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

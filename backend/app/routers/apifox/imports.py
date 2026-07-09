"""Apifox · OpenAPI 导入路由（项目作用域）。"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.apifox import import_service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·导入"])


class ImportRequest(BaseModel):
    url: Optional[str] = None
    content: Optional[str] = None


class ImportReport(BaseModel):
    total: int
    created: int
    skipped: int
    folders_created: int
    schemas_created: int = 0


@router.post("/projects/{pid}/import/openapi", response_model=ImportReport)
def import_openapi(
    pid: int,
    data: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    try:
        if data.url and data.url.strip():
            doc = import_service.fetch_openapi(data.url.strip())
        elif data.content and data.content.strip():
            doc = import_service.parse_content(data.content)
        else:
            raise ValueError("请提供 OpenAPI 的 URL 或粘贴 JSON 内容")
        report = import_service.import_openapi(db, pid, doc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ImportReport(**report)

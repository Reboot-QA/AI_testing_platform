"""Apifox 上传文件 · 业务层（Binary body 用）。

文件字节存 DB；限大小防 DB 膨胀。发送时按 file_id 取字节，校验属本项目。
"""

import json
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.models.apifox.upload_file import ApifoxUploadFile
from app.repositories.apifox import case_repo, endpoint_repo, scenario_repo
from app.repositories.apifox import upload_repo as repo
from app.routers.apifox.upload_schemas import UploadOut

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB，超出 400
# GC 宽限期：只清超过此时长的未引用上传，避免误删「刚上传但用户还没保存接口」的在途文件
UPLOAD_GC_GRACE = timedelta(hours=1)


def _loads(text: Optional[str]) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return {}


def _binary_file_id(spec: Dict[str, Any]) -> Optional[int]:
    body = (spec or {}).get("body") or {}
    if body.get("type") == "binary" and body.get("file_id"):
        try:
            return int(body["file_id"])
        except (TypeError, ValueError):
            return None
    return None


def _out(f: ApifoxUploadFile) -> UploadOut:
    return UploadOut(
        id=f.id, filename=f.filename, content_type=f.content_type,
        size=f.size, created_at=f.created_at,
    )


def create_upload(db: Session, project_id: int, filename: str, content_type: str, data: bytes) -> UploadOut:
    if not data:
        raise ValueError("文件内容为空")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"文件超过 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB 上限")
    obj = ApifoxUploadFile(
        project_id=project_id,
        filename=filename or "file",
        content_type=content_type or "application/octet-stream",
        size=len(data),
        data=data,
    )
    return _out(repo.add(db, obj))


def _referenced_file_ids(db: Session, project_id: int) -> Set[int]:
    """项目内被 binary body 引用的上传文件 id：扫接口 / 用例 / 场景 http 步骤的 request_spec。"""
    refs: Set[int] = set()
    for ep in endpoint_repo.list_endpoints(db, project_id):
        fid = _binary_file_id(_loads(ep.request_spec))
        if fid:
            refs.add(fid)
    for case in case_repo.list_cases_by_project(db, project_id):
        fid = _binary_file_id(_loads(case.request_spec))
        if fid:
            refs.add(fid)
    for scenario in scenario_repo.list_scenarios(db, project_id):
        for step in scenario_repo.list_steps(db, scenario.id):
            if step.type == "http":
                fid = _binary_file_id((_loads(step.config) or {}).get("request_spec") or {})
                if fid:
                    refs.add(fid)
    return refs


def purge_unreferenced_uploads(db: Session, project_id: int, grace: timedelta = UPLOAD_GC_GRACE) -> int:
    """删除本项目不再被任何 binary body 引用、且超过宽限期的上传文件（移除/替换后的孤儿清理）。

    在接口/用例/场景保存后调用。**宽限期**保护「刚上传但用户/他人还没保存接口」的在途文件——
    否则同项目并发的另一次保存会把它当孤儿误删（评审并发点）。
    """
    referenced = _referenced_file_ids(db, project_id)
    cutoff = datetime.utcnow() - grace
    orphans = [
        fid for fid, created in repo.list_id_created_by_project(db, project_id)
        if fid not in referenced and created < cutoff
    ]
    if orphans:
        repo.delete_by_ids(db, orphans)
        db.commit()
    return len(orphans)


def make_binary_loader(db: Session, project_id: int) -> Callable[[int], Optional[Tuple[bytes, str]]]:
    """给 build_request 注入的取字节回调：按 file_id 取，须属本项目，否则 None。"""
    def _load(file_id: int) -> Optional[Tuple[bytes, str]]:
        f = repo.get_file(db, file_id)
        if not f or f.project_id != project_id:
            return None
        return f.data, f.content_type
    return _load

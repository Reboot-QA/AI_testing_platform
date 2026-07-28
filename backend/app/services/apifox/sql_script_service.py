"""Apifox SQL 脚本库 · 业务层（唯一 name、乐观锁、被引用删除拦截、库内调试）。

非法输入 / 被引用删除抛 ValueError（router 转 400）；版本冲突抛 ConflictError（转 409）。
写操作末尾 commit。权限在 router。调试执行任意 SQL（读写皆可）但结果只预览、不写变量。
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.database_conn import ApifoxEnvironmentDatabase
from app.models.apifox.sql_script import ApifoxSqlScript
from app.repositories.apifox import sql_script_repo as repo
from app.routers.apifox.sql_script_schemas import (
    SqlScriptBrief,
    SqlScriptCreate,
    SqlScriptDebugOut,
    SqlScriptOut,
    SqlScriptUpdate,
)
from app.services.apifox import db_executor, versioning

_DEBUG_PREVIEW_ROWS = 100


def _require_unique_name(db: Session, project_id: int, name: str, exclude_id: int | None = None) -> None:
    for s in repo.list_scripts(db, project_id):
        if s.name == name and s.id != exclude_id:
            raise ValueError("SQL 脚本名已存在")


def _out(script: ApifoxSqlScript) -> SqlScriptOut:
    return SqlScriptOut(
        id=script.id,
        project_id=script.project_id,
        name=script.name,
        content=script.content or "",
        description=script.description,
        sort_order=script.sort_order,
        version=script.version,
        created_at=script.created_at,
        updated_at=script.updated_at,
    )


def list_scripts(db: Session, project_id: int) -> List[SqlScriptBrief]:
    return [
        SqlScriptBrief(id=s.id, name=s.name, description=s.description, sort_order=s.sort_order)
        for s in repo.list_scripts(db, project_id)
    ]


def create_script(db: Session, project_id: int, data: SqlScriptCreate) -> SqlScriptOut:
    if not (data.content or "").strip():
        raise ValueError("SQL 内容不能为空")
    _require_unique_name(db, project_id, data.name)
    script = ApifoxSqlScript(
        project_id=project_id,
        name=data.name,
        content=data.content,
        description=data.description,
        sort_order=data.sort_order or 0,
    )
    repo.add(db, script)
    db.commit()
    db.refresh(script)
    return _out(script)


def get_script_out(script: ApifoxSqlScript) -> SqlScriptOut:
    return _out(script)


def update_script(db: Session, script: ApifoxSqlScript, data: SqlScriptUpdate) -> SqlScriptOut:
    # 原子 CAS 先占坑版本（冲突则 rollback + ConflictError，任何字段改动前）
    versioning.bump_version(db, ApifoxSqlScript, script, data.expected_version)
    if data.name is not None and data.name != script.name:
        _require_unique_name(db, script.project_id, data.name, exclude_id=script.id)
        script.name = data.name
    if data.content is not None:
        if not data.content.strip():
            raise ValueError("SQL 内容不能为空")
        script.content = data.content
    if "description" in data.model_fields_set:
        script.description = data.description
    if data.sort_order is not None:
        script.sort_order = data.sort_order
    db.commit()
    db.refresh(script)
    return _out(script)


def delete_script(db: Session, script: ApifoxSqlScript) -> None:
    refs = repo.count_script_refs(db, script.project_id, script.id)
    if refs:
        raise ValueError(f"SQL 脚本被 {refs} 处用例/接口前后置引用，请先解除引用再删除")
    repo.delete(db, script)
    db.commit()


def validate_processor_refs(db: Session, project_id: int, rows) -> None:
    """保存用例/接口时校验前后置里 database_script 引用：缺 sql_script_id 或脚本不存在/不属本项目 → ValueError。"""
    for row in rows or []:
        if getattr(row, "kind", None) != "database_script":
            continue
        sid = getattr(row, "sql_script_id", None)
        if not sid:
            raise ValueError("数据库脚本操作未选择 SQL 脚本")
        script = repo.get_script(db, sid)
        if script is None or script.project_id != project_id:
            raise ValueError(f"引用的 SQL 脚本不存在（id={sid}）")


def debug_sql_script(conn: ApifoxEnvironmentDatabase, content: str) -> SqlScriptDebugOut:
    """库内调试：对指定连接执行 SQL，结果只预览（≤100 行）、不写变量。"""
    if not (content or "").strip():
        raise ValueError("SQL 内容不能为空")
    result = db_executor.run_sql(conn, content)
    return SqlScriptDebugOut(
        status="passed" if result["passed"] else "failed",
        row_count=result["rowcount"],
        preview_rows=result["rows"][:_DEBUG_PREVIEW_ROWS],
        error_message=result.get("error"),
    )

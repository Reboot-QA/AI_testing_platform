"""Apifox 脚本库 · 业务层（唯一 name、lang 校验、被引用删除拦截）。

非法输入/被引用删除抛 ValueError（router 转 400）。写操作末尾 commit。权限在 router。
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.script import ApifoxScript
from app.repositories.apifox import script_repo as repo
from app.routers.apifox.script_schemas import (
    ScriptBrief,
    ScriptCreate,
    ScriptOut,
    ScriptUpdate,
)

VALID_LANGS = {"javascript", "python"}


def _validate_lang(lang: str) -> None:
    if lang not in VALID_LANGS:
        raise ValueError("无效的脚本语言")


def _require_unique_name(db: Session, project_id: int, name: str, exclude_id: int | None = None) -> None:
    for s in repo.list_scripts(db, project_id):
        if s.name == name and s.id != exclude_id:
            raise ValueError("脚本名已存在")


def _out(script: ApifoxScript) -> ScriptOut:
    return ScriptOut(
        id=script.id,
        project_id=script.project_id,
        name=script.name,
        lang=script.lang,
        content=script.content or "",
        description=script.description,
        sort_order=script.sort_order,
        created_at=script.created_at,
        updated_at=script.updated_at,
    )


def list_scripts(db: Session, project_id: int) -> List[ScriptBrief]:
    return [
        ScriptBrief(id=s.id, name=s.name, lang=s.lang, description=s.description, sort_order=s.sort_order)
        for s in repo.list_scripts(db, project_id)
    ]


def create_script(db: Session, project_id: int, data: ScriptCreate) -> ScriptOut:
    _validate_lang(data.lang)
    _require_unique_name(db, project_id, data.name)
    script = ApifoxScript(
        project_id=project_id,
        name=data.name,
        lang=data.lang,
        content=data.content,
        description=data.description,
    )
    repo.add(db, script)
    db.commit()
    db.refresh(script)
    return _out(script)


def get_script_out(script: ApifoxScript) -> ScriptOut:
    return _out(script)


def update_script(db: Session, script: ApifoxScript, data: ScriptUpdate) -> ScriptOut:
    if data.lang is not None:
        _validate_lang(data.lang)
        script.lang = data.lang
    if data.name is not None and data.name != script.name:
        _require_unique_name(db, script.project_id, data.name, exclude_id=script.id)
        script.name = data.name
    if data.content is not None:
        script.content = data.content
    if "description" in data.model_fields_set:
        script.description = data.description
    if data.sort_order is not None:
        script.sort_order = data.sort_order
    db.commit()
    db.refresh(script)
    return _out(script)


def delete_script(db: Session, script: ApifoxScript) -> None:
    refs = repo.count_script_refs(db, script.id)
    if refs:
        raise ValueError(f"脚本被 {refs} 处用例前后置引用，请先解除引用再删除")
    repo.delete(db, script)
    db.commit()

"""Apifox 脚本调试预设 · 数据访问（项目级）。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.script_debug_preset import ApifoxScriptDebugPreset


def list_by_project(db: Session, project_id: int) -> List[ApifoxScriptDebugPreset]:
    return (
        db.query(ApifoxScriptDebugPreset)
        .filter(ApifoxScriptDebugPreset.project_id == project_id)
        .order_by(ApifoxScriptDebugPreset.name.asc())
        .all()
    )


def get_by_name(db: Session, project_id: int, name: str) -> Optional[ApifoxScriptDebugPreset]:
    return (
        db.query(ApifoxScriptDebugPreset)
        .filter(
            ApifoxScriptDebugPreset.project_id == project_id,
            ApifoxScriptDebugPreset.name == name,
        )
        .first()
    )


def get(db: Session, preset_id: int) -> Optional[ApifoxScriptDebugPreset]:
    return db.query(ApifoxScriptDebugPreset).filter(ApifoxScriptDebugPreset.id == preset_id).first()

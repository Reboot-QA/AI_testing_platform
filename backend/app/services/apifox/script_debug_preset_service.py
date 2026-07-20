"""Apifox 脚本调试预设 · 业务层（项目级共享，按名 upsert）。"""

import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.script_debug_preset import ApifoxScriptDebugPreset
from app.repositories.apifox import script_debug_preset_repo as repo
from app.routers.apifox.script_schemas import DebugPresetIn, DebugPresetOut


def _vars(text: Optional[str]) -> Dict[str, str]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return {}
    return {str(k): "" if v is None else str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def _out(preset: ApifoxScriptDebugPreset) -> DebugPresetOut:
    return DebugPresetOut(
        id=preset.id,
        name=preset.name,
        phase=preset.phase,
        variables=_vars(preset.variables),
        response_status=preset.response_status,
        response_body=preset.response_body or "",
    )


def list_presets(db: Session, project_id: int) -> List[DebugPresetOut]:
    return [_out(p) for p in repo.list_by_project(db, project_id)]


def upsert_preset(db: Session, project_id: int, data: DebugPresetIn, user_id: Optional[int]) -> DebugPresetOut:
    """按 (project_id, name) upsert：同名覆盖，否则新建。"""
    preset = repo.get_by_name(db, project_id, data.name)
    if preset is None:
        preset = ApifoxScriptDebugPreset(project_id=project_id, name=data.name, created_by=user_id)
        db.add(preset)
    preset.phase = data.phase
    preset.variables = json.dumps(data.variables, ensure_ascii=False)
    preset.response_status = data.response_status
    preset.response_body = data.response_body
    db.commit()
    db.refresh(preset)
    return _out(preset)


def delete_preset(db: Session, project_id: int, preset_id: int) -> bool:
    """删除本项目下的预设；不属于该项目或不存在返回 False。"""
    preset = repo.get(db, preset_id)
    if preset is None or preset.project_id != project_id:
        return False
    db.delete(preset)
    db.commit()
    return True

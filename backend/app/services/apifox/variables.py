"""Apifox 执行引擎 · 变量解析与插值底座。

{{var}} 文本插值、环境/全局变量解析（local ?? remote，enabled）、多层合并、
用例变量行 / 数据驱动迭代行。处于依赖最底层，无引擎内部依赖，被
request_builder / flow_control / run_engine 复用。
提取的 environment/global 作用域写当前用户本地值（不污染团队远程值）。
"""

import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.repositories.apifox import variable_repo

VARIABLE_PATTERN = re.compile(r"\{\{([^}]+)\}\}")


def apply_vars(text: Optional[str], variables: Dict[str, str]) -> str:
    if not text:
        return ""
    return VARIABLE_PATTERN.sub(
        lambda m: variables.get(m.group(1).strip(), m.group(0)), str(text)
    )


def _loads(text: Optional[str], fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return fallback


def _rows_to_dict(rows: List[Dict[str, Any]], variables: Dict[str, str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for row in rows or []:
        key = str(row.get("key") or "").strip()
        if not key or row.get("enabled") is False:
            continue
        result[key] = apply_vars(str(row.get("value") or ""), variables)
    return result


# ---------- 变量解析（local ?? remote，enabled；user_id=None 为定时模式，只读远程值） ----------
def resolve_env_vars(db: Session, environment_id: Optional[int], user_id: Optional[int]) -> Dict[str, str]:
    if not environment_id:
        return {}
    result: Dict[str, str] = {}
    for var in variable_repo.list_env_vars(db, environment_id):
        if not var.enabled:
            continue
        local = variable_repo.get_env_local(db, var.id, user_id) if user_id is not None else None
        value = local.local_value if local else var.remote_value
        result[var.key] = value or ""
    return result


def resolve_global_vars(db: Session, project_id: int, user_id: Optional[int]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for var in variable_repo.list_global_vars(db, project_id):
        if not var.enabled:
            continue
        local = variable_repo.get_global_local(db, var.id, user_id) if user_id is not None else None
        value = local.local_value if local else var.remote_value
        result[var.key] = value or ""
    return result


def merge_vars(*layers: Dict[str, str]) -> Dict[str, str]:
    """后者覆盖前者：global < env < runtime < case/data_drive。"""
    merged: Dict[str, str] = {}
    for layer in layers:
        merged.update(layer or {})
    return merged


def case_variable_rows(case: ApifoxEndpointCase) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for row in _loads(case.variables, []):
        key = str(row.get("key") or "").strip()
        if key and row.get("enabled") is not False:
            result[key] = str(row.get("value") or "")
    return result


def data_drive_rows(case: ApifoxEndpointCase) -> List[Optional[Dict[str, str]]]:
    """返回执行迭代列表：未启用数据驱动 → [None]；启用 → 各 enabled 行的 values。"""
    drive = _loads(case.data_drive, {})
    result: List[Optional[Dict[str, str]]] = []
    if drive.get("enabled"):
        for row in drive.get("rows") or []:
            if row.get("enabled") is not False:
                result.append(
                    {str(k): str(v or "") for k, v in (row.get("values") or {}).items()}
                )
    if not result:
        result.append(None)
    return result

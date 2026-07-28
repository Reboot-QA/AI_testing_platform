"""Apifox 执行引擎 · 变量解析与插值底座。

{{var}} 文本插值、环境/全局变量解析（local ?? remote，enabled）、多层合并、
用例变量行 / 数据驱动迭代行（单元格 value 可预插值）。处于依赖最底层，无引擎内部依赖，被
request_builder / flow_control / run_engine 复用。
提取的 environment/global 作用域写当前用户本地值（不污染团队远程值）。
"""

import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.repositories.apifox import dataset_repo, variable_repo

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


def resolve_drive_row_values(
    drive_row: Optional[Dict[str, str]],
    *lookup_layers: Dict[str, str],
) -> Optional[Dict[str, str]]:
    """对数据驱动行各 value 做一轮 apply_vars 后再参与 merge。

    lookup 顺序由调用方传入（Spec：global < env < runtime < case，用例最高）；
    不含 drive_row 自身（单元格互引用不在本期）。缺变量保留 {{name}} 原文。
    """
    if not drive_row:
        return drive_row
    lookup = merge_vars(*lookup_layers)
    return {key: apply_vars(value, lookup) for key, value in drive_row.items()}


def case_variable_rows(case: ApifoxEndpointCase) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for row in _loads(case.variables, []):
        key = str(row.get("key") or "").strip()
        if key and row.get("enabled") is not False:
            result[key] = str(row.get("value") or "")
    return result


def _dataset_rows(db: Session, project_id: int, dataset_id: int) -> List[Dict[str, Any]]:
    """拉数据集行（校验属本项目，跨项目忽略）；转成与内联行同构的 {values, enabled}。

    按数据集列定义补齐行内缺失的列（空串）：历史行可能在建列之前写入，values 缺 key。
    不补的话该次迭代不绑定这些变量，`{{列名}}` 会原样发到目标接口。
    """
    dataset = dataset_repo.get_dataset(db, dataset_id)
    if not dataset or dataset.project_id != project_id:
        return []
    raw_columns = _loads(dataset.columns, [])
    columns = [str(c) for c in raw_columns if str(c)] if isinstance(raw_columns, list) else []
    rows: List[Dict[str, Any]] = []
    for r in dataset_repo.list_rows(db, dataset_id):
        values = _loads(r.values, {})
        if not isinstance(values, dict):  # 脏数据降级，勿让执行 500
            values = {}
        for col in columns:
            values.setdefault(col, "")
        rows.append({"values": values, "enabled": r.enabled})
    return rows


def data_drive_rows(
    case: ApifoxEndpointCase, db: Optional[Session] = None
) -> List[Optional[Dict[str, str]]]:
    """返回执行迭代列表：未启用 → [None]；内联 → 各 enabled 行；数据集源 → 数据集各 enabled 行。

    source=dataset 需传 db 解析项目级数据集（缺 db 或数据集不存在则视为无行）。
    """
    drive = _loads(case.data_drive, {})
    if not drive.get("enabled"):
        return [None]
    if drive.get("source") == "dataset" and drive.get("dataset_id") and db is not None:
        try:
            rows = _dataset_rows(db, case.project_id, int(drive["dataset_id"]))
        except (ValueError, TypeError):
            rows = []  # 非法 dataset_id（绕过 schema 的写入路径）兑现文档承诺：视为无行
    else:
        rows = drive.get("rows") or []
    result: List[Optional[Dict[str, str]]] = [
        {str(k): str(v or "") for k, v in (row.get("values") or {}).items()}
        for row in rows
        if row.get("enabled") is not False
    ]
    return result or [None]

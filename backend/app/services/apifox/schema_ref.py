"""Apifox 数据模型 · 跨模型 $ref 解析与引用提取。

模型间用 {"$ref": "#/models/<模型名>"} 互相引用（名在项目内唯一）。契约校验前把跨模型
$ref 递归内联成自包含 JSON Schema；环/未知引用/超深降级为 {type: object}（校验类需健壮，
不抛异常）。名称提取供引用计数与保存时的环检测复用。
"""

import json
from typing import Any, Optional, Set

from sqlalchemy.orm import Session

from app.repositories.apifox import schema_repo

MODEL_REF_PREFIX = "#/models/"
_MAX_REF_DEPTH = 10


def _ref_name(node: Any) -> Optional[str]:
    """节点若是 {"$ref": "#/models/X"} 则返回被引用模型名 X，否则 None。"""
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith(MODEL_REF_PREFIX):
            return ref[len(MODEL_REF_PREFIX):]
    return None


def _walk_collect(node: Any, names: Set[str]) -> None:
    name = _ref_name(node)
    if name:
        names.add(name)
        return
    if isinstance(node, dict):
        for value in node.values():
            _walk_collect(value, names)
    elif isinstance(node, list):
        for value in node:
            _walk_collect(value, names)


def extract_model_refs(json_schema_text: Optional[str]) -> Set[str]:
    """收集一段 json_schema 文本里所有 #/models/<名> 引用的模型名（去重）。非法 JSON 返回空集。"""
    if not json_schema_text:
        return set()
    try:
        root = json.loads(json_schema_text)
    except (ValueError, TypeError):
        return set()
    names: Set[str] = set()
    _walk_collect(root, names)
    return names


def _inline(db: Session, project_id: int, node: Any, depth: int, seen: frozenset) -> Any:
    if depth > _MAX_REF_DEPTH:
        return {"type": "object"}
    name = _ref_name(node)
    if name:
        if name in seen:
            return {"type": "object"}  # 环引用降级
        try:
            schema = schema_repo.get_schema_by_name(db, project_id, name)
        except Exception:  # noqa: BLE001 - 校验类工具需健壮：DB 异常同样降级，绝不外抛
            return {"type": "object"}  # 否则异常冒泡至无 try/finally 的单跑路径会卡 running
        if not schema or not schema.json_schema:
            return {"type": "object"}  # 未知引用降级
        try:
            target = json.loads(schema.json_schema)
        except (ValueError, TypeError):
            return {"type": "object"}
        return _inline(db, project_id, target, depth + 1, seen | {name})
    if isinstance(node, dict):
        return {key: _inline(db, project_id, value, depth, seen) for key, value in node.items()}
    if isinstance(node, list):
        return [_inline(db, project_id, value, depth, seen) for value in node]
    return node


def resolve_schema_text(db: Session, project_id: int, json_schema_text: Optional[str]) -> str:
    """把文本里的跨模型 $ref 递归内联为自包含 JSON Schema，返回 JSON 文本。

    未知引用/环/超深降级为 {type: object}，保证 fastjsonschema 可编译。无 $ref 时结构等价返回。
    """
    if not json_schema_text:
        return "{}"
    try:
        root = json.loads(json_schema_text)
    except (ValueError, TypeError):
        return json_schema_text
    resolved = _inline(db, project_id, root, depth=0, seen=frozenset())
    return json.dumps(resolved, ensure_ascii=False, default=str)

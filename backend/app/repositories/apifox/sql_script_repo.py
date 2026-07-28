"""Apifox SQL 脚本库 · 数据访问层。不含业务校验；不提交事务。

引用不走关联表：SQL 脚本被前后置 processor JSON 里 kind=database_script 的 sql_script_id 引用，
故引用计数扫描用例 / 接口的 pre/post_processors 文本。
"""

import json
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.apifox.sql_script import ApifoxSqlScript


def list_scripts(db: Session, project_id: int) -> List[ApifoxSqlScript]:
    return (
        db.query(ApifoxSqlScript)
        .filter(ApifoxSqlScript.project_id == project_id)
        .order_by(ApifoxSqlScript.sort_order, ApifoxSqlScript.id)
        .all()
    )


def get_script(db: Session, script_id: int) -> Optional[ApifoxSqlScript]:
    return db.query(ApifoxSqlScript).filter(ApifoxSqlScript.id == script_id).first()


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj) -> None:
    db.delete(obj)


def _refs_in(text: Optional[str], script_id: int) -> int:
    """统计一段 processor JSON 里 kind=database_script 且 sql_script_id 命中的项数。"""
    if not text:
        return 0
    try:
        rows = json.loads(text)
    except (ValueError, TypeError):
        return 0
    if not isinstance(rows, list):
        return 0
    return sum(
        1
        for r in rows
        if isinstance(r, dict) and r.get("kind") == "database_script" and r.get("sql_script_id") == script_id
    )


def count_script_refs(db: Session, project_id: int, script_id: int) -> int:
    """用例与接口两处前后置 JSON 引用都算，避免删掉仍被引用的 SQL 脚本。"""
    total = 0
    cases = (
        db.query(ApifoxEndpointCase.pre_processors, ApifoxEndpointCase.post_processors)
        .filter(ApifoxEndpointCase.project_id == project_id)
        .all()
    )
    for pre, post in cases:
        total += _refs_in(pre, script_id) + _refs_in(post, script_id)
    endpoints = (
        db.query(ApifoxEndpoint.pre_processors, ApifoxEndpoint.post_processors)
        .filter(ApifoxEndpoint.project_id == project_id)
        .all()
    )
    for pre, post in endpoints:
        total += _refs_in(pre, script_id) + _refs_in(post, script_id)
    return total

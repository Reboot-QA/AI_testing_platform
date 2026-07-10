"""Apifox 工作台 · 数据访问层（跨项目只读聚合，仅在给定可见项目集内查询）。"""

from datetime import datetime
from typing import Dict, List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.apifox.run import ApifoxRun
from app.models.apifox.scenario import ApifoxScenario
from app.models.apifox.variable import ApifoxEnvironment


def _count_by_project(db: Session, model, project_ids: List[int]) -> Dict[int, int]:
    if not project_ids:
        return {}
    rows = (
        db.query(model.project_id, func.count(model.id))
        .filter(model.project_id.in_(project_ids))
        .group_by(model.project_id)
        .all()
    )
    return {pid: count for pid, count in rows}


def count_endpoints(db: Session, project_ids: List[int]) -> Dict[int, int]:
    return _count_by_project(db, ApifoxEndpoint, project_ids)


def count_scenarios(db: Session, project_ids: List[int]) -> Dict[int, int]:
    return _count_by_project(db, ApifoxScenario, project_ids)


def count_cases(db: Session, project_ids: List[int]) -> Dict[int, int]:
    return _count_by_project(db, ApifoxEndpointCase, project_ids)


def list_running(db: Session, project_ids: List[int]) -> List[ApifoxRun]:
    if not project_ids:
        return []
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.project_id.in_(project_ids), ApifoxRun.status == "running")
        .order_by(ApifoxRun.id.desc())
        .all()
    )


def recent_runs(db: Session, project_ids: List[int], limit: int = 10) -> List[ApifoxRun]:
    # 不按 status 过滤：running 记录会同时出现在「最近报告」，前端按状态区分渲染
    if not project_ids:
        return []
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.project_id.in_(project_ids))
        .order_by(ApifoxRun.id.desc())
        .limit(limit)
        .all()
    )


def today_totals(db: Session, project_ids: List[int], since: datetime) -> Tuple[int, int]:
    """当日已结束 run 的（通过数之和, 总数之和），用于今日通过率。"""
    if not project_ids:
        return (0, 0)
    passed_sum, total_sum = (
        db.query(
            func.coalesce(func.sum(ApifoxRun.passed_count), 0),
            func.coalesce(func.sum(ApifoxRun.total_count), 0),
        )
        .filter(
            ApifoxRun.project_id.in_(project_ids),
            ApifoxRun.status.in_(("passed", "failed")),
            ApifoxRun.started_at >= since,
        )
        .one()
    )
    return (int(passed_sum or 0), int(total_sum or 0))


def environment_names(db: Session, project_ids: List[int]) -> Dict[int, str]:
    if not project_ids:
        return {}
    rows = (
        db.query(ApifoxEnvironment.id, ApifoxEnvironment.name)
        .filter(ApifoxEnvironment.project_id.in_(project_ids))
        .all()
    )
    return {env_id: name for env_id, name in rows}

"""Apifox 工作台 · 数据访问层（跨项目只读聚合，仅在给定可见项目集内查询）。"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.apifox.ai_gen_task import ApifoxAiGenTask
from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.models.apifox.scenario import ApifoxScenario
from app.models.apifox.schedule import ApifoxSchedule
from app.models.apifox.suite import ApifoxSuite
from app.models.apifox.variable import ApifoxEnvironment
from app.models.hub_ai_task import HubAiTask
from app.models.test_execution import ManualTestRun


def _count_by_project(db: Session, model, project_ids: List[int]) -> Dict[int, int]:
    if not project_ids:
        return {}
    query = db.query(model.project_id, func.count(model.id)).filter(
        model.project_id.in_(project_ids)
    )
    if hasattr(model, "deleted_at"):  # 回收站中的项不计入概览统计
        query = query.filter(model.deleted_at.is_(None))
    rows = query.group_by(model.project_id).all()
    return {pid: count for pid, count in rows}


def count_endpoints(db: Session, project_ids: List[int]) -> Dict[int, int]:
    return _count_by_project(db, ApifoxEndpoint, project_ids)


def count_scenarios(db: Session, project_ids: List[int]) -> Dict[int, int]:
    return _count_by_project(db, ApifoxScenario, project_ids)


def count_cases(db: Session, project_ids: List[int]) -> Dict[int, int]:
    return _count_by_project(db, ApifoxEndpointCase, project_ids)


def count_suites(db: Session, project_ids: List[int]) -> Dict[int, int]:
    return _count_by_project(db, ApifoxSuite, project_ids)


def daily_trend(db: Session, project_id: int, days: int = 7) -> Dict[str, Tuple[int, int]]:
    """近 days 天按日聚合（通过数之和, 失败数之和）。仅统计已结束 run（passed/failed）。

    分母取「实际执行数 = passed + failed」而非 total_count：total_count 是建 run 时的计划条数，
    循环/重试等流程控制会让实际执行数超过它，用它当分母会算出 >100% 的通过率（图会被 y 轴截断）。
    与单次 run 自身的 pass_rate 口径一致。

    返回 {日期字符串: (passed_sum, failed_sum)}；缺失的日期由 service 补零。DATE() 在 sqlite/mysql 均可用。
    """
    since = (datetime.utcnow() - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    rows = (
        db.query(
            func.date(ApifoxRun.started_at),
            func.coalesce(func.sum(ApifoxRun.passed_count), 0),
            func.coalesce(func.sum(ApifoxRun.failed_count), 0),
        )
        .filter(
            ApifoxRun.project_id == project_id,
            ApifoxRun.status.in_(("passed", "failed")),
            ApifoxRun.started_at >= since,
        )
        .group_by(func.date(ApifoxRun.started_at))
        .all()
    )
    return {str(d): (int(p or 0), int(f or 0)) for d, p, f in rows}


def list_running(db: Session, project_ids: List[int]) -> List[ApifoxRun]:
    if not project_ids:
        return []
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.project_id.in_(project_ids), ApifoxRun.status == "running")
        .order_by(ApifoxRun.id.desc())
        .all()
    )


def count_running(db: Session, project_ids: List[int]) -> int:
    if not project_ids:
        return 0
    return (
        db.query(func.count(ApifoxRun.id))
        .filter(ApifoxRun.project_id.in_(project_ids), ApifoxRun.status == "running")
        .scalar()
        or 0
    )


def list_running_page(db: Session, project_ids: List[int], page: int, page_size: int) -> List[ApifoxRun]:
    if not project_ids:
        return []
    offset = (page - 1) * page_size
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.project_id.in_(project_ids), ApifoxRun.status == "running")
        .order_by(ApifoxRun.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )


def _apply_run_filters(query, status: str | None, target_type: str | None):
    if status:
        query = query.filter(ApifoxRun.status == status)
    if target_type:
        query = query.filter(ApifoxRun.target_type == target_type)
    return query


def count_runs(
    db: Session, project_ids: List[int], status: str | None = None, target_type: str | None = None
) -> int:
    if not project_ids:
        return 0
    q = db.query(func.count(ApifoxRun.id)).filter(ApifoxRun.project_id.in_(project_ids))
    return _apply_run_filters(q, status, target_type).scalar() or 0


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


def recent_runs_page(
    db: Session,
    project_ids: List[int],
    page: int,
    page_size: int,
    status: str | None = None,
    target_type: str | None = None,
) -> List[ApifoxRun]:
    if not project_ids:
        return []
    offset = (page - 1) * page_size
    q = _apply_run_filters(
        db.query(ApifoxRun).filter(ApifoxRun.project_id.in_(project_ids)), status, target_type
    )
    return q.order_by(ApifoxRun.id.desc()).offset(offset).limit(page_size).all()


def count_failures(db: Session, project_ids: List[int]) -> int:
    if not project_ids:
        return 0
    return (
        db.query(func.count(ApifoxRun.id))
        .filter(ApifoxRun.project_id.in_(project_ids), ApifoxRun.status == "failed")
        .scalar()
        or 0
    )


def list_failures_page(
    db: Session, project_ids: List[int], page: int, page_size: int
) -> List[ApifoxRun]:
    if not project_ids:
        return []
    offset = (page - 1) * page_size
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.project_id.in_(project_ids), ApifoxRun.status == "failed")
        .order_by(ApifoxRun.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )


def failure_reasons(db: Session, run_ids: List[int]) -> Dict[int, str]:
    """每个运行的失败原因：取其首个带 error_message 的失败步骤（按步骤 id 升序）。"""
    if not run_ids:
        return {}
    rows = (
        db.query(ApifoxRunStep.run_id, ApifoxRunStep.error_message)
        .filter(
            ApifoxRunStep.run_id.in_(run_ids),
            ApifoxRunStep.status == "failed",
            ApifoxRunStep.error_message.isnot(None),
        )
        .order_by(ApifoxRunStep.run_id, ApifoxRunStep.id)
        .all()
    )
    reasons: Dict[int, str] = {}
    for run_id, msg in rows:
        if run_id not in reasons and msg:
            reasons[run_id] = msg
    return reasons


def count_schedules(db: Session, project_ids: List[int]) -> int:
    if not project_ids:
        return 0
    return (
        db.query(func.count(ApifoxSchedule.id))
        .filter(
            ApifoxSchedule.project_id.in_(project_ids),
            ApifoxSchedule.enabled.is_(True),
            ApifoxSchedule.next_run_at.isnot(None),
        )
        .scalar()
        or 0
    )


def list_schedules_page(
    db: Session, project_ids: List[int], page: int, page_size: int
) -> List[ApifoxSchedule]:
    """启用且有下次执行时间的定时任务，按 next_run_at 升序（最近将执行的在前）。"""
    if not project_ids:
        return []
    offset = (page - 1) * page_size
    return (
        db.query(ApifoxSchedule)
        .filter(
            ApifoxSchedule.project_id.in_(project_ids),
            ApifoxSchedule.enabled.is_(True),
            ApifoxSchedule.next_run_at.isnot(None),
        )
        .order_by(ApifoxSchedule.next_run_at.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )


def count_manual_runs(db: Session, project_ids: List[int]) -> int:
    if not project_ids:
        return 0
    return (
        db.query(func.count(ManualTestRun.id))
        .filter(ManualTestRun.project_id.in_(project_ids))
        .scalar()
        or 0
    )


def list_manual_runs_page(
    db: Session, project_ids: List[int], page: int, page_size: int
) -> List[ManualTestRun]:
    if not project_ids:
        return []
    offset = (page - 1) * page_size
    return (
        db.query(ManualTestRun)
        .filter(ManualTestRun.project_id.in_(project_ids))
        .order_by(ManualTestRun.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )


def today_totals(db: Session, project_ids: List[int], since: datetime) -> Tuple[int, int]:
    """当日已结束 run 的（通过数之和, 实际执行数之和），用于今日通过率。

    实际执行数 = passed + failed，同 daily_trend，不用 total_count 这个计划数当分母。
    """
    if not project_ids:
        return (0, 0)
    passed_sum, failed_sum = (
        db.query(
            func.coalesce(func.sum(ApifoxRun.passed_count), 0),
            func.coalesce(func.sum(ApifoxRun.failed_count), 0),
        )
        .filter(
            ApifoxRun.project_id.in_(project_ids),
            ApifoxRun.status.in_(("passed", "failed")),
            ApifoxRun.started_at >= since,
        )
        .one()
    )
    passed = int(passed_sum or 0)
    return (passed, passed + int(failed_sum or 0))


def count_hub_ai_tasks(db: Session, project_ids: List[int]) -> int:
    if not project_ids:
        return 0
    return (
        db.query(func.count(HubAiTask.id))
        .filter(HubAiTask.project_id.in_(project_ids))
        .scalar()
        or 0
    )


def count_apifox_ai_gen_tasks(db: Session, project_ids: List[int]) -> int:
    if not project_ids:
        return 0
    return (
        db.query(func.count(ApifoxAiGenTask.id))
        .filter(ApifoxAiGenTask.project_id.in_(project_ids))
        .scalar()
        or 0
    )


def list_hub_ai_tasks_recent(db: Session, project_ids: List[int], limit: int) -> List[HubAiTask]:
    if not project_ids or limit <= 0:
        return []
    return (
        db.query(HubAiTask)
        .filter(HubAiTask.project_id.in_(project_ids))
        .order_by(HubAiTask.updated_at.desc(), HubAiTask.id.desc())
        .limit(limit)
        .all()
    )


def list_apifox_ai_gen_tasks_recent(
    db: Session, project_ids: List[int], limit: int
) -> List[ApifoxAiGenTask]:
    if not project_ids or limit <= 0:
        return []
    return (
        db.query(ApifoxAiGenTask)
        .filter(ApifoxAiGenTask.project_id.in_(project_ids))
        .order_by(ApifoxAiGenTask.updated_at.desc(), ApifoxAiGenTask.id.desc())
        .limit(limit)
        .all()
    )


def environment_names(db: Session, project_ids: List[int]) -> Dict[int, str]:
    if not project_ids:
        return {}
    rows = (
        db.query(ApifoxEnvironment.id, ApifoxEnvironment.name)
        .filter(ApifoxEnvironment.project_id.in_(project_ids))
        .all()
    )
    return {env_id: name for env_id, name in rows}

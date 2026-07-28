"""Apifox 运行记录 · 数据访问层。不含业务校验；提交时机由 run_service 控制（流式逐步落库）。"""

from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.run import ApifoxRun, ApifoxRunStep


def list_case_runs_by_endpoint(db: Session, endpoint_id: int, limit: int = 200) -> List[ApifoxRun]:
    """列某接口下所有用例的运行记录（供接口维度「测试报告」，按接口 case 精确过滤、不受项目级 100 条窗口影响）。"""
    case_ids = select(ApifoxEndpointCase.id).where(ApifoxEndpointCase.endpoint_id == endpoint_id)
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.target_type == "case", ApifoxRun.target_id.in_(case_ids))
        .order_by(ApifoxRun.id.desc())
        .limit(limit)
        .all()
    )


# 相邻两条 started_at 间隔超过该值（秒）则视为不同轮「全部运行/连续执行」
_ENDPOINT_RUN_BATCH_GAP_SECONDS = 120


def latest_batch_case_runs_by_endpoint(db: Session, endpoint_id: int) -> List[ApifoxRun]:
    """接口测试报告：只返回最近一次连续运行批次（如「全部运行」），不含更早历史。"""
    runs = list_case_runs_by_endpoint(db, endpoint_id)
    if not runs:
        return []
    ordered = sorted(runs, key=lambda r: r.started_at, reverse=True)
    batch: List[ApifoxRun] = [ordered[0]]
    gap = _ENDPOINT_RUN_BATCH_GAP_SECONDS
    for i in range(1, len(ordered)):
        prev_t = ordered[i - 1].started_at
        cur_t = ordered[i].started_at
        if (prev_t - cur_t).total_seconds() > gap:
            break
        batch.append(ordered[i])
    return batch


def list_runs(db: Session, project_id: int, limit: int = 100) -> List[ApifoxRun]:
    # 仅列顶层运行（套件子运行不刷屏；子运行从父运行 drill-down 进入）
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.project_id == project_id, ApifoxRun.parent_run_id.is_(None))
        .order_by(ApifoxRun.id.desc())
        .limit(limit)
        .all()
    )


def _top_level_runs_query(
    db: Session,
    project_id: int,
    target_types: Optional[List[str]] = None,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    query = db.query(ApifoxRun).filter(
        ApifoxRun.project_id == project_id, ApifoxRun.parent_run_id.is_(None)
    )
    if target_types:
        query = query.filter(ApifoxRun.target_type.in_(target_types))
    if status:
        query = query.filter(ApifoxRun.status == status)
    if keyword and keyword.strip():
        query = query.filter(ApifoxRun.target_name.like(f"%{keyword.strip()}%"))
    if date_from:
        query = query.filter(ApifoxRun.started_at >= datetime.combine(date_from, time.min))
    if date_to:
        # 闭区间：含 date_to 当天全天，故上界取次日零点开区间
        query = query.filter(
            ApifoxRun.started_at < datetime.combine(date_to, time.min) + timedelta(days=1)
        )
    return query


def count_runs(
    db: Session,
    project_id: int,
    target_types: Optional[List[str]] = None,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> int:
    return (
        _top_level_runs_query(db, project_id, target_types, keyword, status, date_from, date_to)
        .with_entities(func.count(ApifoxRun.id))
        .scalar()
        or 0
    )


def list_runs_page(
    db: Session,
    project_id: int,
    page: int,
    page_size: int,
    target_types: Optional[List[str]] = None,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[ApifoxRun]:
    offset = (page - 1) * page_size
    return (
        _top_level_runs_query(db, project_id, target_types, keyword, status, date_from, date_to)
        .order_by(ApifoxRun.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )


def failure_reasons(db: Session, run_ids: List[int]) -> Dict[int, str]:
    """取每个运行的首个失败步骤原因；套件父运行会继续查找其首个失败子运行。"""
    if not run_ids:
        return {}

    direct_rows = (
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
    for run_id, message in direct_rows:
        if run_id not in reasons and message:
            reasons[run_id] = message

    unresolved = [run_id for run_id in run_ids if run_id not in reasons]
    if not unresolved:
        return reasons

    child_rows = (
        db.query(ApifoxRun.parent_run_id, ApifoxRunStep.error_message)
        .join(ApifoxRunStep, ApifoxRunStep.run_id == ApifoxRun.id)
        .filter(
            ApifoxRun.parent_run_id.in_(unresolved),
            ApifoxRun.status == "failed",
            ApifoxRunStep.status == "failed",
            ApifoxRunStep.error_message.isnot(None),
        )
        .order_by(ApifoxRun.parent_run_id, ApifoxRun.id, ApifoxRunStep.id)
        .all()
    )
    for parent_run_id, message in child_rows:
        if parent_run_id not in reasons and message:
            reasons[parent_run_id] = message
    return reasons


def get_run(db: Session, run_id: int) -> Optional[ApifoxRun]:
    return db.query(ApifoxRun).filter(ApifoxRun.id == run_id).first()


def list_child_runs(db: Session, parent_run_id: int) -> List[ApifoxRun]:
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.parent_run_id == parent_run_id)
        .order_by(ApifoxRun.id)
        .all()
    )


def list_steps(db: Session, run_id: int) -> List[ApifoxRunStep]:
    return (
        db.query(ApifoxRunStep)
        .filter(ApifoxRunStep.run_id == run_id)
        .order_by(ApifoxRunStep.id)
        .all()
    )


def delete_runs(db: Session, run_ids: List[int]) -> int:
    """删除运行及其步骤；若含套件父运行，一并删除子运行。"""
    if not run_ids:
        return 0
    child_rows = db.query(ApifoxRun.id).filter(ApifoxRun.parent_run_id.in_(run_ids)).all()
    all_ids = list({*run_ids, *(row[0] for row in child_rows)})
    db.query(ApifoxRun).filter(ApifoxRun.id.in_(all_ids)).update(
        {ApifoxRun.parent_run_id: None}, synchronize_session=False
    )
    db.query(ApifoxRunStep).filter(ApifoxRunStep.run_id.in_(all_ids)).delete(
        synchronize_session=False
    )
    return db.query(ApifoxRun).filter(ApifoxRun.id.in_(all_ids)).delete(synchronize_session=False)


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def mark_running_interrupted(db: Session) -> int:
    """把卡在 running 的运行标记为 failed（启动回收：SSE 运行不跨重启，running 必是上次进程被杀残留）。"""
    runs = db.query(ApifoxRun).filter(ApifoxRun.status == "running").all()
    if not runs:
        return 0
    now = datetime.utcnow()
    run_ids = [r.id for r in runs]
    for r in runs:
        r.status = "failed"
        if r.finished_at is None:
            r.finished_at = now
        total = (r.passed_count or 0) + (r.failed_count or 0)
        r.pass_rate = round((r.passed_count or 0) / total * 100, 2) if total else 0.0
    db.query(ApifoxRunStep).filter(
        ApifoxRunStep.run_id.in_(run_ids), ApifoxRunStep.status == "running"
    ).update({ApifoxRunStep.status: "failed"}, synchronize_session=False)
    return len(runs)

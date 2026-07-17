"""Apifox 运行记录 · 数据访问层。不含业务校验；提交时机由 run_service 控制（流式逐步落库）。"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
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


def list_runs(db: Session, project_id: int, limit: int = 100) -> List[ApifoxRun]:
    # 仅列顶层运行（套件子运行不刷屏；子运行从父运行 drill-down 进入）
    return (
        db.query(ApifoxRun)
        .filter(ApifoxRun.project_id == project_id, ApifoxRun.parent_run_id.is_(None))
        .order_by(ApifoxRun.id.desc())
        .limit(limit)
        .all()
    )


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

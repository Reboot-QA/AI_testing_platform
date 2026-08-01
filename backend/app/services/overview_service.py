"""项目域概览 · 聚合统计（功能测试 / 需求测试）。"""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.apifox.ai_gen_task import ApifoxAiGenTask
from app.models.hub_ai_task import HubAiTask
from app.models.requirement import Requirement
from app.models.test_execution import ManualTestRun
from app.models.testcase import TestCase


def _linked_requirement_ids_select(db: Session, project_id: int):
    return (
        select(TestCase.requirement_id)
        .where(
            TestCase.project_id == project_id,
            TestCase.requirement_id.isnot(None),
        )
        .distinct()
    )


def get_functional_overview(db: Session, project_id: int) -> dict:
    case_total = int(
        db.query(func.count(TestCase.id)).filter(TestCase.project_id == project_id).scalar() or 0
    )
    pending_review_count = int(
        db.query(func.count(TestCase.id))
        .filter(TestCase.project_id == project_id, TestCase.review_status == "pending")
        .scalar()
        or 0
    )
    ai_generated_count = int(
        db.query(func.count(TestCase.id))
        .filter(TestCase.project_id == project_id, TestCase.source == "ai_generated")
        .scalar()
        or 0
    )
    ai_pending_review_count = int(
        db.query(func.count(TestCase.id))
        .filter(
            TestCase.project_id == project_id,
            TestCase.source == "ai_generated",
            TestCase.review_status == "pending",
        )
        .scalar()
        or 0
    )
    running_run_count = int(
        db.query(func.count(ManualTestRun.id))
        .filter(ManualTestRun.project_id == project_id, ManualTestRun.status == "running")
        .scalar()
        or 0
    )
    last_run = (
        db.query(ManualTestRun)
        .filter(ManualTestRun.project_id == project_id, ManualTestRun.status == "finished")
        .order_by(ManualTestRun.finished_at.desc(), ManualTestRun.id.desc())
        .first()
    )
    last_completed_pass_rate: Optional[float] = None
    if last_run is not None:
        last_completed_pass_rate = float(last_run.pass_rate)

    return {
        "case_total": case_total,
        "pending_review_count": pending_review_count,
        "ai_generated_count": ai_generated_count,
        "ai_pending_review_count": ai_pending_review_count,
        "running_run_count": running_run_count,
        "last_completed_pass_rate": last_completed_pass_rate,
    }


def get_requirements_overview(db: Session, project_id: int) -> dict:
    req_total = int(
        db.query(func.count(Requirement.id)).filter(Requirement.project_id == project_id).scalar() or 0
    )
    unreviewed_count = int(
        db.query(func.count(Requirement.id))
        .filter(Requirement.project_id == project_id, Requirement.status != "approved")
        .scalar()
        or 0
    )
    linked_ids = _linked_requirement_ids_select(db, project_id)
    linked_count = int(
        db.query(func.count(Requirement.id))
        .filter(Requirement.project_id == project_id, Requirement.id.in_(linked_ids))
        .scalar()
        or 0
    )
    unlinked_count = max(req_total - linked_count, 0)
    ai_document_count = int(
        db.query(func.count(Requirement.id))
        .filter(Requirement.project_id == project_id, Requirement.source == "ai_document")
        .scalar()
        or 0
    )
    ai_unreviewed_count = int(
        db.query(func.count(Requirement.id))
        .filter(
            Requirement.project_id == project_id,
            Requirement.source == "ai_document",
            Requirement.status != "approved",
        )
        .scalar()
        or 0
    )

    return {
        "req_total": req_total,
        "unreviewed_count": unreviewed_count,
        "linked_count": linked_count,
        "unlinked_count": unlinked_count,
        "ai_document_count": ai_document_count,
        "ai_unreviewed_count": ai_unreviewed_count,
    }


def get_ai_tasks_overview(db: Session, project_id: int) -> dict:
    """AI 任务概述：三类任务均为可追踪的执行记录（hub_ai_tasks + apifox AI 生成任务）。"""
    api_task_count = int(
        db.query(func.count(ApifoxAiGenTask.id))
        .filter(ApifoxAiGenTask.project_id == project_id)
        .scalar()
        or 0
    )
    active_api_task_count = int(
        db.query(func.count(ApifoxAiGenTask.id))
        .filter(
            ApifoxAiGenTask.project_id == project_id,
            ApifoxAiGenTask.status.in_(("pending", "running")),
        )
        .scalar()
        or 0
    )
    requirement_task_count = int(
        db.query(func.count(HubAiTask.id))
        .filter(HubAiTask.project_id == project_id, HubAiTask.task_type == "requirement")
        .scalar()
        or 0
    )
    case_task_count = int(
        db.query(func.count(HubAiTask.id))
        .filter(HubAiTask.project_id == project_id, HubAiTask.task_type == "functional")
        .scalar()
        or 0
    )
    total_task_count = api_task_count + requirement_task_count + case_task_count

    return {
        "total_task_count": total_task_count,
        "requirement_task_count": requirement_task_count,
        "case_task_count": case_task_count,
        "api_task_count": api_task_count,
        "active_api_task_count": active_api_task_count,
    }

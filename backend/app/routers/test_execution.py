from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.project import Project
from app.models.test_execution import ManualTestRun, ManualTestRunCase
from app.models.testcase import TestCase
from app.models.user import User
from app.schemas import (
    ManualTestRunCaseOut,
    ManualTestRunCaseResultUpdate,
    ManualTestRunCreate,
    ManualTestRunDetailOut,
    ManualTestRunSummaryOut,
    ManualTestRunUpdate,
)
from app.services.test_execution_service import create_manual_run, get_executor_name, submit_case_result

router = APIRouter(prefix="/test-executions", tags=["用例执行"])


def _check_project(db: Session, project_id: int, user_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _get_owned_run(db: Session, run_id: int, user: User) -> ManualTestRun:
    run = db.query(ManualTestRun).filter(ManualTestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="测试单不存在")
    _check_project(db, run.project_id, user.id)
    return run


def _case_out(db: Session, item: ManualTestRunCase) -> ManualTestRunCaseOut:
    case = item.testcase or db.query(TestCase).filter(TestCase.id == item.testcase_id).first()
    return ManualTestRunCaseOut(
        id=item.id,
        run_id=item.run_id,
        testcase_id=item.testcase_id,
        sort_order=item.sort_order,
        result=item.result,
        actual_result=item.actual_result,
        remark=item.remark,
        executed_by=item.executed_by,
        executor_name=get_executor_name(db, item.executed_by),
        executed_at=item.executed_at,
        case_title=case.title if case else "",
        case_priority=case.priority if case else "",
        case_type=case.case_type if case else "",
        preconditions=case.preconditions if case else None,
        steps=case.steps if case else None,
        expected_results=case.expected_results if case else None,
        requirement_id=case.requirement_id if case else None,
    )


def _summary_out(db: Session, run: ManualTestRun) -> ManualTestRunSummaryOut:
    return ManualTestRunSummaryOut(
        id=run.id,
        project_id=run.project_id,
        name=run.name,
        build_name=run.build_name,
        description=run.description,
        status=run.status,
        executor_id=run.executor_id,
        executor_name=get_executor_name(db, run.executor_id),
        total_count=run.total_count,
        passed_count=run.passed_count,
        failed_count=run.failed_count,
        blocked_count=run.blocked_count,
        skipped_count=run.skipped_count,
        pending_count=run.pending_count,
        pass_rate=run.pass_rate,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


def _detail_out(db: Session, run: ManualTestRun) -> ManualTestRunDetailOut:
    cases = (
        db.query(ManualTestRunCase)
        .filter(ManualTestRunCase.run_id == run.id)
        .order_by(ManualTestRunCase.sort_order.asc(), ManualTestRunCase.id.asc())
        .all()
    )
    summary = _summary_out(db, run)
    return ManualTestRunDetailOut(
        **summary.model_dump(),
        cases=[_case_out(db, item) for item in cases],
    )


@router.get("", response_model=List[ManualTestRunSummaryOut])
def list_runs(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, project_id, current_user.id)
    runs = (
        db.query(ManualTestRun)
        .filter(ManualTestRun.project_id == project_id)
        .order_by(ManualTestRun.id.desc())
        .all()
    )
    return [_summary_out(db, run) for run in runs]


@router.post("", response_model=ManualTestRunDetailOut)
def create_run(
    data: ManualTestRunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, data.project_id, current_user.id)

    case_ids = list(data.case_ids)
    if data.requirement_id is not None:
        req_cases = (
            db.query(TestCase.id)
            .filter(
                TestCase.project_id == data.project_id,
                TestCase.requirement_id == data.requirement_id,
                TestCase.review_status == "approved",
            )
            .all()
        )
        allowed = {row[0] for row in req_cases}
        case_ids = [cid for cid in case_ids if cid in allowed]
        if not case_ids:
            raise HTTPException(status_code=400, detail="所选需求下没有可执行的已通过用例")

    try:
        run = create_manual_run(
            db,
            project_id=data.project_id,
            name=data.name,
            case_ids=case_ids,
            executor_id=current_user.id,
            build_name=data.build_name,
            description=data.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _detail_out(db, run)


@router.get("/available-cases/list")
def list_available_cases(
    project_id: int,
    requirement_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project(db, project_id, current_user.id)
    query = db.query(TestCase).filter(
        TestCase.project_id == project_id,
        TestCase.review_status == "approved",
    )
    if requirement_id is not None:
        query = query.filter(TestCase.requirement_id == requirement_id)
    cases = query.order_by(TestCase.id.desc()).all()
    return [
        {
            "id": case.id,
            "title": case.title,
            "priority": case.priority,
            "case_type": case.case_type,
            "requirement_id": case.requirement_id,
        }
        for case in cases
    ]


@router.get("/{run_id}", response_model=ManualTestRunDetailOut)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _get_owned_run(db, run_id, current_user)
    return _detail_out(db, run)


@router.put("/{run_id}", response_model=ManualTestRunSummaryOut)
def update_run(
    run_id: int,
    data: ManualTestRunUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _get_owned_run(db, run_id, current_user)
    if data.name is not None:
        run.name = data.name.strip()
    if data.build_name is not None:
        run.build_name = data.build_name.strip() or None
    if data.description is not None:
        run.description = data.description.strip() or None
    db.commit()
    db.refresh(run)
    return _summary_out(db, run)


@router.delete("/{run_id}")
def delete_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _get_owned_run(db, run_id, current_user)
    db.delete(run)
    db.commit()
    return {"message": "测试单已删除"}


@router.put("/{run_id}/cases/{case_row_id}", response_model=ManualTestRunCaseOut)
def update_case_result(
    run_id: int,
    case_row_id: int,
    data: ManualTestRunCaseResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = _get_owned_run(db, run_id, current_user)
    run_case = (
        db.query(ManualTestRunCase)
        .filter(ManualTestRunCase.id == case_row_id, ManualTestRunCase.run_id == run.id)
        .first()
    )
    if not run_case:
        raise HTTPException(status_code=404, detail="执行用例不存在")

    try:
        submit_case_result(
            db,
            run=run,
            run_case=run_case,
            result=data.result,
            user_id=current_user.id,
            actual_result=data.actual_result,
            remark=data.remark,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _case_out(db, run_case)

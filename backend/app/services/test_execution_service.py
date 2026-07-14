from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.test_execution import ManualTestRun, ManualTestRunCase
from app.models.testcase import TestCase
from app.models.user import User
from app.utils.time_util import now_local

EXECUTION_RESULTS = {"pending", "pass", "fail", "blocked", "skip"}


def _recount_run(db: Session, run: ManualTestRun) -> None:
    cases = db.query(ManualTestRunCase).filter(ManualTestRunCase.run_id == run.id).all()
    passed = failed = blocked = skipped = pending = 0
    for item in cases:
        if item.result == "pass":
            passed += 1
        elif item.result == "fail":
            failed += 1
        elif item.result == "blocked":
            blocked += 1
        elif item.result == "skip":
            skipped += 1
        else:
            pending += 1

    total = len(cases)
    run.total_count = total
    run.passed_count = passed
    run.failed_count = failed
    run.blocked_count = blocked
    run.skipped_count = skipped
    run.pending_count = pending
    executed = passed + failed + blocked + skipped
    run.pass_rate = round((passed / executed) * 100, 2) if executed else 0.0

    if pending == 0 and total > 0:
        run.status = "finished"
        if not run.finished_at:
            run.finished_at = now_local()
    elif executed > 0:
        run.status = "running"
        if not run.started_at:
            run.started_at = now_local()
    else:
        run.status = "waiting"


def create_manual_run(
    db: Session,
    *,
    project_id: int,
    name: str,
    case_ids: List[int],
    executor_id: int,
    build_name: Optional[str] = None,
    description: Optional[str] = None,
) -> ManualTestRun:
    unique_ids = list(dict.fromkeys(case_ids))
    cases = (
        db.query(TestCase)
        .filter(
            TestCase.project_id == project_id,
            TestCase.id.in_(unique_ids),
            TestCase.review_status == "approved",
        )
        .order_by(TestCase.id.asc())
        .all()
    )
    if len(cases) != len(unique_ids):
        raise ValueError("部分用例不存在或未通过评审，无法加入测试单")

    run = ManualTestRun(
        project_id=project_id,
        name=name.strip(),
        build_name=(build_name or "").strip() or None,
        description=(description or "").strip() or None,
        executor_id=executor_id,
        status="waiting",
    )
    db.add(run)
    db.flush()

    for index, case in enumerate(cases):
        db.add(
            ManualTestRunCase(
                run_id=run.id,
                testcase_id=case.id,
                sort_order=index,
                result="pending",
            )
        )

    db.flush()
    _recount_run(db, run)
    db.commit()
    db.refresh(run)
    return run


def submit_case_result(
    db: Session,
    *,
    run: ManualTestRun,
    run_case: ManualTestRunCase,
    result: str,
    user_id: int,
    actual_result: Optional[str] = None,
    remark: Optional[str] = None,
) -> ManualTestRunCase:
    if result not in EXECUTION_RESULTS - {"pending"}:
        raise ValueError("执行结果无效，支持 pass / fail / blocked / skip")

    run_case.result = result
    run_case.actual_result = (actual_result or "").strip() or None
    run_case.remark = (remark or "").strip() or None
    run_case.executed_by = user_id
    run_case.executed_at = now_local()

    _recount_run(db, run)
    db.commit()
    db.refresh(run_case)
    db.refresh(run)
    return run_case


def get_executor_name(db: Session, user_id: Optional[int]) -> str:
    if not user_id:
        return ""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return ""
    return user.username

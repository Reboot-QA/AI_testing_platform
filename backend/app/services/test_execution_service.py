from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.test_execution import ManualTestRun, ManualTestRunCase
from app.models.testcase import TestCase
from app.models.user import User
from app.services.testcase_query_helper import sort_testcases_for_display, testcase_has_sort_order_column, testcase_sort_order_value
from app.utils.time_util import now_local

EXECUTION_RESULTS = {"pending", "pass", "fail", "blocked", "skip"}


def sort_run_cases_by_library_order(cases: List[ManualTestRunCase]) -> List[ManualTestRunCase]:
    """与功能用例库一致：testcase.sort_order 降序，再 id 降序。"""

    def _key(item: ManualTestRunCase) -> tuple:
        case = item.testcase
        if case is None:
            return (0, item.sort_order, item.id)
        if testcase_has_sort_order_column():
            seq = testcase_sort_order_value(case) or case.id
            return (-seq, -case.id, item.id)
        return (-case.id, item.id)

    return sorted(cases, key=_key)


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


def delete_testcases_with_execution_cleanup(db: Session, cases: List[TestCase]) -> int:
    """删除功能用例，并清理手工测试单中的关联行后重算统计。"""
    if not cases:
        return 0

    case_ids = [case.id for case in cases]
    run_cases = (
        db.query(ManualTestRunCase)
        .filter(ManualTestRunCase.testcase_id.in_(case_ids))
        .all()
    )
    affected_run_ids = {item.run_id for item in run_cases}
    for item in run_cases:
        db.delete(item)
    if run_cases:
        db.flush()
        for run_id in affected_run_ids:
            run = db.query(ManualTestRun).filter(ManualTestRun.id == run_id).first()
            if run:
                _recount_run(db, run)

    for case in cases:
        db.delete(case)
    return len(cases)


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
        .all()
    )
    if len(cases) != len(unique_ids):
        raise ValueError("部分用例不存在或未通过评审，无法加入测试单")

    cases = sort_testcases_for_display(cases)

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

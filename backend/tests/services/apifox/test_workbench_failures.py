"""工作台「失败聚焦」数据访问：跨项目失败运行筛选 + 失败原因取首个失败步骤 error_message。"""

from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.repositories.apifox import workbench_repo as repo


def _run(db, project_id: int, status: str) -> ApifoxRun:
    r = ApifoxRun(project_id=project_id, target_type="scenario", target_id=1, target_name="场景", status=status)
    db.add(r)
    db.flush()
    return r


def _step(db, run_id: int, status: str, error: str | None = None) -> ApifoxRunStep:
    s = ApifoxRunStep(run_id=run_id, status=status, case_name="步骤", error_message=error)
    db.add(s)
    db.flush()
    return s


def test_count_and_list_failures_scoped_to_projects(db):
    r1 = _run(db, 1, "failed")
    _run(db, 1, "passed")
    _run(db, 1, "running")
    _run(db, 2, "failed")  # 其它项目，应被隔离
    db.commit()

    assert repo.count_failures(db, [1]) == 1
    runs = repo.list_failures_page(db, [1], 1, 20)
    assert [r.id for r in runs] == [r1.id]


def test_failure_reasons_takes_first_failed_step_with_message(db):
    r = _run(db, 1, "failed")
    _step(db, r.id, "passed", None)
    _step(db, r.id, "failed", None)  # 失败但无原因，跳过
    _step(db, r.id, "failed", "断言失败：HTTP 状态码期望 200，实际 401")
    _step(db, r.id, "failed", "第二个失败原因")
    db.commit()

    reasons = repo.failure_reasons(db, [r.id])
    assert reasons[r.id] == "断言失败：HTTP 状态码期望 200，实际 401"


def test_failure_reasons_empty_when_no_message(db):
    r = _run(db, 1, "failed")
    _step(db, r.id, "failed", None)
    db.commit()

    assert repo.failure_reasons(db, [r.id]) == {}


def test_failure_reasons_empty_run_ids(db):
    assert repo.failure_reasons(db, []) == {}

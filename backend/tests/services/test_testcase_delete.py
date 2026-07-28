from app.models.project import Project
from app.models.test_execution import ManualTestRun, ManualTestRunCase
from app.models.testcase import TestCase
from app.models.user import User
from app.services.test_execution_service import delete_testcases_with_execution_cleanup


def _seed_case_in_run(db):
    user = User(username="tester", hashed_password="hashed", role="tester")
    db.add(user)
    db.flush()

    project = Project(name="项目", owner_id=user.id)
    db.add(project)
    db.flush()

    case = TestCase(project_id=project.id, title="待删除用例", review_status="approved")
    db.add(case)
    db.flush()

    run = ManualTestRun(project_id=project.id, name="测试单", executor_id=user.id)
    db.add(run)
    db.flush()

    db.add(ManualTestRunCase(run_id=run.id, testcase_id=case.id, sort_order=0))
    db.commit()
    db.refresh(run)
    db.refresh(case)
    return run, case


def test_delete_testcases_cleans_manual_run_cases(db):
    run, case = _seed_case_in_run(db)

    deleted = delete_testcases_with_execution_cleanup(db, [case])
    db.commit()

    assert deleted == 1
    assert db.query(TestCase).filter(TestCase.id == case.id).first() is None
    assert db.query(ManualTestRunCase).filter(ManualTestRunCase.testcase_id == case.id).count() == 0

    refreshed_run = db.query(ManualTestRun).filter(ManualTestRun.id == run.id).first()
    assert refreshed_run is not None
    assert refreshed_run.total_count == 0
    assert refreshed_run.pending_count == 0

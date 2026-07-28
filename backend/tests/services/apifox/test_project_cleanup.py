"""purge_project_all 级联清理回归测试。

覆盖：硬删项目应清空其手工执行 + 需求/用例 + apifox 全部数据，且**不波及其他项目**。
sqlite 不强制 FK，本测试断言的是"删对了哪些行 + 隔离性"。
（老「接口自动化」模块已下线、遗留表已移除，不再覆盖。）
"""

from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.test_execution import ManualTestRun, ManualTestRunCase
from app.models.testcase import TestCase as TCase  # 避免 pytest 误当测试类收集
from app.models.user_project_pref import UserProjectPref
from app.services.apifox.project_cleanup import purge_project_all


def _seed_project(db, name: str) -> int:
    """建一个项目并铺满各表数据，返回 project_id。"""
    project = Project(name=name, owner_id=1)
    db.add(project)
    db.flush()
    pid = project.id

    req = Requirement(project_id=pid, title=f"{name}-需求")
    db.add(req)
    db.flush()
    case = TCase(project_id=pid, requirement_id=req.id, title=f"{name}-用例")
    db.add(case)
    db.flush()

    mrun = ManualTestRun(project_id=pid, name=f"{name}-手工执行")
    db.add(mrun)
    db.flush()
    db.add(ManualTestRunCase(run_id=mrun.id, testcase_id=case.id))

    db.add(ApifoxEndpoint(project_id=pid, name="apifox接口", method="GET", path="/y"))
    db.add(UserProjectPref(user_id=1, project_id=pid, pinned=True, sort_order=0))
    db.commit()
    return pid


def _count_for_project(db, pid: int) -> dict:
    """统计各表中直接/间接属于该项目的行数。"""
    mrun_ids = [m.id for m in db.query(ManualTestRun).filter(ManualTestRun.project_id == pid).all()]
    return {
        "requirement": db.query(Requirement).filter(Requirement.project_id == pid).count(),
        "testcase": db.query(TCase).filter(TCase.project_id == pid).count(),
        "mrun": db.query(ManualTestRun).filter(ManualTestRun.project_id == pid).count(),
        "mrun_case": db.query(ManualTestRunCase)
        .filter(ManualTestRunCase.run_id.in_(mrun_ids or [-1]))
        .count(),
        "apifox_ep": db.query(ApifoxEndpoint).filter(ApifoxEndpoint.project_id == pid).count(),
        "pref": db.query(UserProjectPref).filter(UserProjectPref.project_id == pid).count(),
    }


def test_purge_project_all_wipes_target_project(db):
    pid = _seed_project(db, "目标")
    before = _count_for_project(db, pid)
    assert all(v > 0 for v in before.values()), f"前置数据未铺满: {before}"

    purge_project_all(db, pid)
    db.commit()

    after = _count_for_project(db, pid)
    assert all(v == 0 for v in after.values()), f"仍有残留: {after}"


def test_purge_project_all_isolates_other_projects(db):
    target = _seed_project(db, "目标")
    other = _seed_project(db, "旁观")
    other_before = _count_for_project(db, other)

    purge_project_all(db, target)
    db.commit()

    other_after = _count_for_project(db, other)
    assert other_after == other_before, f"误伤旁观项目: {other_before} -> {other_after}"

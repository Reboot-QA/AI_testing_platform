"""接口维度测试报告 · run_repo.list_case_runs_by_endpoint（按接口的用例精确过滤运行记录）。"""

from app.models.apifox.run import ApifoxRun
from app.repositories.apifox import run_repo
from app.routers.apifox.case_schemas import CaseCreate
from app.services.apifox import case_service


def _case_id(db, endpoint):
    return case_service.create_case(db, endpoint.project_id, endpoint.id, CaseCreate(name="c")).id


def _run(db, target_type, target_id, project_id=1):
    r = ApifoxRun(project_id=project_id, target_type=target_type, target_id=target_id, target_name="x")
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_returns_only_this_endpoints_case_runs(db, make_endpoint):
    ep1 = make_endpoint(name="ep1")
    ep2 = make_endpoint(name="ep2")
    r1 = _run(db, "case", _case_id(db, ep1))
    _run(db, "case", _case_id(db, ep2))  # 另一接口的用例运行，不应返回

    runs = run_repo.list_case_runs_by_endpoint(db, ep1.id)

    assert [r.id for r in runs] == [r1.id]


def test_excludes_non_case_runs_on_same_id(db, make_endpoint):
    ep = make_endpoint()
    cid = _case_id(db, ep)
    case_run = _run(db, "case", cid)
    _run(db, "scenario", cid)  # target_id 相同但 type=scenario，不匹配

    runs = run_repo.list_case_runs_by_endpoint(db, ep.id)

    assert [r.id for r in runs] == [case_run.id]

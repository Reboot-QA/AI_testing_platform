"""接口「全部运行」聚合报告 · iter_endpoint_batch_run / list_endpoint_batch_runs。"""

from app.models.apifox.run import ApifoxRun
from app.repositories.apifox import run_repo
from app.routers.apifox.case_schemas import CaseCreate
from app.services.apifox import case_service, run_service


def _case_id(db, endpoint):
    return case_service.create_case(db, endpoint.project_id, endpoint.id, CaseCreate(name="c1")).id


def test_endpoint_batch_run_creates_parent_and_children(db, make_endpoint):
    ep = make_endpoint(method="POST", path="/login")
    c1 = case_service.create_case(db, ep.project_id, ep.id, CaseCreate(name="a"))
    c2 = case_service.create_case(db, ep.project_id, ep.id, CaseCreate(name="b"))

    events = list(
        run_service.iter_endpoint_batch_run(db, ep, [c1, c2], None, "tester", 1)
    )

    assert any(e.get("type") == "batch_start" for e in events)
    parent_id = next(e["run_id"] for e in events if e.get("type") == "batch_start")
    parent = run_repo.get_run(db, parent_id)
    assert parent is not None
    assert parent.target_type == "endpoint"
    assert parent.target_id == ep.id
    assert parent.parent_run_id is None

    children = run_repo.list_child_runs(db, parent_id)
    assert len(children) == 2
    assert {c.target_id for c in children} == {c1.id, c2.id}
    assert all(c.parent_run_id == parent_id for c in children)


def test_list_endpoint_batch_runs_returns_parents_only(db, make_endpoint):
    ep = make_endpoint()
    cid = _case_id(db, ep)
    parent = ApifoxRun(
        project_id=ep.project_id,
        target_type="endpoint",
        target_id=ep.id,
        target_name="POST /x",
        total_count=1,
    )
    child = ApifoxRun(
        project_id=ep.project_id,
        target_type="case",
        target_id=cid,
        target_name="c",
        parent_run_id=None,
    )
    db.add_all([parent, child])
    db.commit()
    db.refresh(parent)
    child.parent_run_id = parent.id
    db.commit()

    rows = run_repo.list_endpoint_batch_runs(db, ep.id)

    assert [r.id for r in rows] == [parent.id]

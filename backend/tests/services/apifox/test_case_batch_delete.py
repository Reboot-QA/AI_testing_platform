"""接口用例 · 批量软删除 + 来源(origin)标记。"""

from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep
from app.repositories.apifox import case_repo
from app.routers.apifox.case_schemas import CaseCreate
from app.services.apifox import case_service as svc


def test_bulk_create_marks_origin_ai(db, make_endpoint):
    ep = make_endpoint(project_id=1, name="登录")
    created, _skipped, _failed = svc.create_cases_bulk(
        db, 1, ep.id, [CaseCreate(name="AI 用例", category="negative")], origin="ai"
    )

    assert created == 1
    case = next(c for c in case_repo.list_cases(db, ep.id) if c.name == "AI 用例")
    assert case.origin == "ai"


def test_single_create_defaults_manual(db, make_endpoint):
    ep = make_endpoint(project_id=1, name="登录2")
    out = svc.create_case(db, 1, ep.id, CaseCreate(name="手工用例"))

    case = case_repo.get_case(db, out.id)
    assert case.origin == "manual"


def test_batch_delete_soft_deletes_selected(db, make_endpoint):
    ep = make_endpoint(project_id=1, name="登录3")
    svc.create_cases_bulk(
        db, 1, ep.id,
        [CaseCreate(name="a"), CaseCreate(name="b"), CaseCreate(name="c")],
    )
    ids = [c.id for c in case_repo.list_cases(db, ep.id) if c.name in ("a", "b")]

    deleted, blocked, _details = svc.batch_delete_cases(db, ep.id, ids, deleted_by=7)

    assert deleted == 2 and blocked == []
    remaining = [c.name for c in case_repo.list_cases(db, ep.id)]
    assert remaining == ["c"]  # 只剩未删的


def test_batch_delete_ignores_foreign_ids(db, make_endpoint):
    ep = make_endpoint(project_id=1, name="登录4")
    svc.create_cases_bulk(db, 1, ep.id, [CaseCreate(name="x")])
    keep_id = case_repo.list_cases(db, ep.id)[0].id

    # 传入不属于该接口的 id（越权）→ 忽略，不误删
    deleted, _blocked, _details = svc.batch_delete_cases(db, ep.id, [999999], deleted_by=None)

    assert deleted == 0
    assert case_repo.get_case(db, keep_id).deleted_at is None


def test_batch_delete_with_detach_refs(db, make_endpoint):
    ep = make_endpoint(project_id=1, name="登录5")
    out = svc.create_case(db, 1, ep.id, CaseCreate(name="被引用"))
    case = case_repo.get_case(db, out.id)
    s = ApifoxScenario(project_id=1, name="登录场景")
    db.add(s)
    db.commit()
    db.add(ApifoxScenarioStep(scenario_id=s.id, type="case", ref_case_id=case.id))
    db.commit()

    deleted, blocked, _details = svc.batch_delete_cases(
        db, ep.id, [case.id], deleted_by=1, detach_refs=False
    )
    assert deleted == 0 and blocked == ["被引用"]

    deleted2, blocked2, _ = svc.batch_delete_cases(
        db, ep.id, [case.id], deleted_by=1, detach_refs=True
    )
    assert deleted2 == 1 and blocked2 == []
    assert case_repo.get_case(db, case.id).deleted_at is not None

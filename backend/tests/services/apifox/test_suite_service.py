"""测试套件 · CRUD + 套件项校验 + bulk replace + 展示回显 + 级联删除。

被测：app/services/apifox/suite_service.py。仅业务逻辑，sqlite 隔离库。
"""

import pytest

from app.routers.apifox.scenario_schemas import ScenarioCreate
from app.routers.apifox.suite_schemas import SuiteCreate, SuiteItemIn, SuiteUpdate
from app.services.apifox import scenario_service
from app.services.apifox import suite_service as svc


def _case_item(case_id, enabled=True):
    return SuiteItemIn(target_type="case", target_id=case_id, enabled=enabled)


def _scenario_item(scenario_id):
    return SuiteItemIn(target_type="scenario", target_id=scenario_id)


def _make_scenario(db, project_id=1, name="scn"):
    return scenario_service.create_scenario(
        db, project_id=project_id, data=ScenarioCreate(name=name, steps=[])
    )


def test_create_suite_with_valid_items_persists_ordered(db, make_case):
    a, b = make_case(name="A"), make_case(name="B")
    scn = _make_scenario(db, name="S")

    out = svc.create_suite(
        db, project_id=1,
        data=SuiteCreate(name="套件", items=[_case_item(a.id), _scenario_item(scn.id), _case_item(b.id)]),
    )

    assert [(i.target_type, i.target_id) for i in out.items] == [
        ("case", a.id), ("scenario", scn.id), ("case", b.id)
    ]


def test_create_suite_case_item_wrong_project_rejected(db, make_case):
    other = make_case(project_id=999, name="别项目用例")

    with pytest.raises(ValueError, match="用例不存在或不属于该项目"):
        svc.create_suite(db, project_id=1, data=SuiteCreate(name="x", items=[_case_item(other.id)]))


def test_create_suite_scenario_item_not_exist_rejected(db):
    with pytest.raises(ValueError, match="场景不存在或不属于该项目"):
        svc.create_suite(db, project_id=1, data=SuiteCreate(name="x", items=[_scenario_item(123456)]))


def test_create_suite_invalid_target_type_rejected(db, make_case):
    a = make_case(name="A")
    bad = SuiteItemIn(target_type="endpoint", target_id=a.id)

    with pytest.raises(ValueError, match="套件项类型非法"):
        svc.create_suite(db, project_id=1, data=SuiteCreate(name="x", items=[bad]))


def test_update_suite_replaces_items(db, make_case):
    a, b, c = make_case(name="A"), make_case(name="B"), make_case(name="C")
    out = svc.create_suite(db, project_id=1, data=SuiteCreate(name="x", items=[_case_item(a.id)]))
    suite = svc.repo.get_suite(db, out.id)

    updated = svc.update_suite(db, suite, SuiteUpdate(items=[_case_item(b.id), _case_item(c.id)]))

    assert [i.target_id for i in updated.items] == [b.id, c.id]


def test_update_suite_empty_items_clears(db, make_case):
    a = make_case(name="A")
    out = svc.create_suite(db, project_id=1, data=SuiteCreate(name="x", items=[_case_item(a.id)]))
    suite = svc.repo.get_suite(db, out.id)

    updated = svc.update_suite(db, suite, SuiteUpdate(items=[]))

    assert updated.items == []


def test_item_out_carries_display_fields(db, make_endpoint, make_case):
    ep = make_endpoint(method="POST", path="/orders", name="下单")
    case = make_case(name="建单用例", endpoint=ep)
    scn = _make_scenario(db, name="下单链路")

    out = svc.create_suite(
        db, project_id=1, data=SuiteCreate(name="x", items=[_case_item(case.id), _scenario_item(scn.id)])
    )

    case_item, scenario_item = out.items
    assert case_item.target_name == "建单用例"
    assert case_item.endpoint_method == "POST"
    assert scenario_item.target_name == "下单链路"


def test_item_out_deleted_target_name_empty(db, make_case):
    case = make_case(name="将删")
    out = svc.create_suite(db, project_id=1, data=SuiteCreate(name="x", items=[_case_item(case.id)]))
    suite = svc.repo.get_suite(db, out.id)
    from app.repositories.apifox import case_repo
    case_repo.delete(db, case)
    db.commit()

    reloaded = svc.get_suite_out(db, suite)

    assert reloaded.items[0].target_name == ""


def test_delete_suite_removes_items(db, make_case):
    a = make_case(name="A")
    out = svc.create_suite(db, project_id=1, data=SuiteCreate(name="x", items=[_case_item(a.id)]))
    suite = svc.repo.get_suite(db, out.id)

    svc.delete_suite(db, suite)

    assert svc.repo.get_suite(db, out.id) is None
    assert svc.repo.list_items(db, out.id) == []


def test_list_suites_item_count(db, make_case):
    a, b = make_case(name="A"), make_case(name="B")
    svc.create_suite(db, project_id=1, data=SuiteCreate(name="两项", items=[_case_item(a.id), _case_item(b.id)]))

    briefs = svc.list_suites(db, project_id=1)

    assert len(briefs) == 1
    assert briefs[0].item_count == 2

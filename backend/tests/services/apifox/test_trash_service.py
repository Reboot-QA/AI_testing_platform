"""回收站 · 软删除聚合 + 还原 + 彻底删（垂直切片：场景/套件/用例三类）。

被测：app/services/apifox/trash_service.py 及 scenario/suite/case_service 的软删/还原/彻底删。
sqlite 隔离库，仅业务层。
"""

from datetime import datetime, timedelta

import pytest

from app.routers.apifox.scenario_schemas import ScenarioCreate, StepIn
from app.routers.apifox.suite_schemas import SuiteCreate, SuiteItemIn
from app.services.apifox import (
    case_service,
    endpoint_service,
    scenario_service,
    suite_service,
)
from app.services.apifox import trash_service as svc


def _make_scenario(db, name="scn"):
    return scenario_service.create_scenario(db, project_id=1, data=ScenarioCreate(name=name, steps=[]))


def _make_suite(db, case_id, name="套件"):
    return suite_service.create_suite(
        db, project_id=1,
        data=SuiteCreate(name=name, items=[SuiteItemIn(target_type="case", target_id=case_id)]),
    )


def test_soft_deleted_entities_appear_in_trash_newest_first(db, make_case):
    case = make_case(name="用例A")
    scn = _make_scenario(db, name="场景A")
    suite = _make_suite(db, case.id, name="套件A")

    case_service.delete_case(db, case_service.repo.get_case(db, case.id))
    scenario_service.delete_scenario(db, scenario_service.repo.get_scenario(db, scn.id))
    suite_service.delete_suite(db, suite_service.repo.get_suite(db, suite.id))

    trash = svc.list_trash(db, project_id=1)

    kinds = {(t.kind, t.name) for t in trash}
    assert ("case", "用例A") in kinds
    assert ("scenario", "场景A") in kinds
    assert ("suite", "套件A") in kinds
    # 统一按删除时间倒序：最后删的套件在最前
    assert trash[0].deleted_at >= trash[-1].deleted_at


def test_trash_scoped_to_project(db, make_case):
    case = make_case(project_id=1, name="本项目")
    other = make_case(project_id=999, name="别项目")
    case_service.delete_case(db, case_service.repo.get_case(db, case.id))
    case_service.delete_case(db, case_service.repo.get_case(db, other.id))

    trash = svc.list_trash(db, project_id=1)

    assert [t.name for t in trash if t.kind == "case"] == ["本项目"]


def test_restore_scenario_returns_to_list(db):
    scn = _make_scenario(db, name="待还原")
    obj = scenario_service.repo.get_scenario(db, scn.id)
    scenario_service.delete_scenario(db, obj)
    assert scenario_service.list_scenarios(db, project_id=1) == []

    scenario_service.restore_scenario(db, obj)

    names = [s.name for s in scenario_service.list_scenarios(db, project_id=1)]
    assert names == ["待还原"]
    assert svc.list_trash(db, project_id=1) == []


def test_purge_case_hard_removes_row(db, make_case):
    case = make_case(name="将彻底删")
    obj = case_service.repo.get_case(db, case.id)
    case_service.delete_case(db, obj)

    case_service.purge_case(db, obj)

    assert case_service.repo.get_case(db, case.id) is None
    assert svc.list_trash(db, project_id=1) == []


# ---------- 接口（单接口）软删除 ----------
def test_deleted_endpoint_appears_in_trash_as_endpoint_kind(db, make_endpoint):
    ep = make_endpoint(name="待删接口", method="POST", path="/orders")

    endpoint_service.delete_endpoint(db, endpoint_service.repo.get_endpoint(db, ep.id))

    trash = svc.list_trash(db, project_id=1)
    item = next(t for t in trash if t.kind == "endpoint")
    assert item.name == "待删接口"
    assert item.detail == "POST /orders"
    # 保留期 30 天：到期时间 = 删除时间 + 30 天
    assert item.expires_at == item.deleted_at + timedelta(days=svc.TRASH_RETENTION_DAYS)


def test_soft_deleted_endpoint_hidden_from_tree(db, make_endpoint):
    ep = make_endpoint(name="隐藏接口")

    endpoint_service.delete_endpoint(db, endpoint_service.repo.get_endpoint(db, ep.id))

    assert endpoint_service.list_endpoints(db, project_id=1) == []


def test_restore_endpoint_returns_to_tree(db, make_endpoint):
    ep = make_endpoint(name="待还原接口")
    obj = endpoint_service.repo.get_endpoint(db, ep.id)
    endpoint_service.delete_endpoint(db, obj)

    endpoint_service.restore_endpoint(db, obj)

    names = [e.name for e in endpoint_service.list_endpoints(db, project_id=1)]
    assert names == ["待还原接口"]
    assert svc.list_trash(db, project_id=1) == []


def test_delete_endpoint_blocked_when_case_referenced_by_scenario(db, make_case):
    case = make_case(name="被引用用例")
    scenario_service.create_scenario(
        db,
        project_id=1,
        data=ScenarioCreate(
            name="引用场景", steps=[StepIn(type="case", ref_case_id=case.id)]
        ),
    )
    ep = endpoint_service.repo.get_endpoint(db, case.endpoint_id)

    with pytest.raises(ValueError, match="场景步骤引用"):
        endpoint_service.delete_endpoint(db, ep)

    # 被拦截：接口未进回收站，仍在树中
    assert [e.id for e in endpoint_service.list_endpoints(db, project_id=1)] == [ep.id]


def test_purge_endpoint_cascades_cases(db, make_case, make_endpoint):
    ep = make_endpoint(name="带用例接口")
    case = make_case(name="随接口清除", endpoint=ep)
    obj = endpoint_service.repo.get_endpoint(db, ep.id)
    endpoint_service.delete_endpoint(db, obj)

    endpoint_service.purge_endpoint(db, obj)

    assert endpoint_service.repo.get_endpoint(db, ep.id) is None
    assert case_service.repo.get_case(db, case.id) is None


def test_trash_records_operator_name(db, make_endpoint):
    from app.models.user import User

    user = User(username="alice", full_name="爱丽丝", hashed_password="x")
    db.add(user)
    db.commit()
    ep = make_endpoint(name="带操作人接口")

    endpoint_service.delete_endpoint(
        db, endpoint_service.repo.get_endpoint(db, ep.id), deleted_by=user.id
    )

    item = next(t for t in svc.list_trash(db, project_id=1) if t.kind == "endpoint")
    assert item.operator == "alice"  # 展示登录账号 username


def test_trash_operator_none_when_no_deleter(db, make_endpoint):
    ep = make_endpoint(name="无操作人接口")

    endpoint_service.delete_endpoint(db, endpoint_service.repo.get_endpoint(db, ep.id))

    item = next(t for t in svc.list_trash(db, project_id=1) if t.kind == "endpoint")
    assert item.operator is None


def test_purge_expired_removes_only_items_past_retention(db, make_endpoint):
    fresh = make_endpoint(name="新删接口")
    old = make_endpoint(name="过期接口")
    endpoint_service.delete_endpoint(db, endpoint_service.repo.get_endpoint(db, fresh.id))
    old_obj = endpoint_service.repo.get_endpoint(db, old.id)
    endpoint_service.delete_endpoint(db, old_obj)
    # 手动把过期项的删除时间调到保留期之外
    old_obj.deleted_at = datetime.utcnow() - timedelta(days=svc.TRASH_RETENTION_DAYS + 1)
    db.commit()

    purged = svc.purge_expired(db)

    assert purged == 1
    assert endpoint_service.repo.get_endpoint(db, old.id) is None
    assert endpoint_service.repo.get_endpoint(db, fresh.id) is not None


def test_batch_restore_multiple_items(db, make_case, make_endpoint):
    case = make_case(name="批量用例")
    ep = make_endpoint(name="批量接口")
    scn = _make_scenario(db, name="批量场景")

    case_service.delete_case(db, case_service.repo.get_case(db, case.id))
    endpoint_service.delete_endpoint(db, endpoint_service.repo.get_endpoint(db, ep.id))
    scenario_service.delete_scenario(db, scenario_service.repo.get_scenario(db, scn.id))

    from app.routers.apifox.trash_schemas import TrashBatchItemIn

    result = svc.batch_restore(
        db,
        1,
        [
            TrashBatchItemIn(kind="case", id=case.id),
            TrashBatchItemIn(kind="endpoint", id=ep.id),
            TrashBatchItemIn(kind="scenario", id=scn.id),
        ],
    )

    assert result.succeeded == 3
    assert result.failed == 0
    assert svc.list_trash(db, project_id=1) == []


def test_batch_purge_multiple_items(db, make_case, make_endpoint):
    case = make_case(name="批量删用例")
    ep = make_endpoint(name="批量删接口")
    case_service.delete_case(db, case_service.repo.get_case(db, case.id))
    endpoint_service.delete_endpoint(db, endpoint_service.repo.get_endpoint(db, ep.id))

    from app.routers.apifox.trash_schemas import TrashBatchItemIn

    result = svc.batch_purge(
        db,
        1,
        [
            TrashBatchItemIn(kind="case", id=case.id),
            TrashBatchItemIn(kind="endpoint", id=ep.id),
        ],
    )

    assert result.succeeded == 2
    assert result.failed == 0
    assert svc.list_trash(db, project_id=1) == []


def test_batch_restore_skips_missing_item(db, make_endpoint):
    from app.routers.apifox.trash_schemas import TrashBatchItemIn

    result = svc.batch_restore(db, 1, [TrashBatchItemIn(kind="endpoint", id=99999)])

    assert result.succeeded == 0
    assert result.failed == 1


def test_list_trash_page(db, make_case):
    for i in range(3):
        case = make_case(name=f"分页用例{i}")
        case_service.delete_case(db, case_service.repo.get_case(db, case.id))

    page1 = svc.list_trash_page(db, 1, page=1, page_size=2)
    assert page1.total == 3
    assert page1.page == 1
    assert len(page1.items) == 2
    page2 = svc.list_trash_page(db, 1, page=2, page_size=2)
    assert len(page2.items) == 1

    filtered = svc.list_trash_page(db, 1, page=1, page_size=10, keyword="分页用例1")
    assert filtered.total == 1
    assert filtered.items[0].name == "分页用例1"

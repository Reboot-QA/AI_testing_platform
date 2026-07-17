"""Apifox 场景排序持久化 · service 集成测试（sqlite 隔离库）。

覆盖：组内重排、跨组移动（到文件夹/到未分组）、只更新传入 id、非法 id、跨项目、非法 folder。
方案 A 快照重编号：只发受影响的组，后端只更新传入 id。
"""

import pytest

from app.models.apifox.endpoint import ApifoxFolder
from app.models.apifox.scenario import ApifoxScenario
from app.repositories.apifox import scenario_repo as repo
from app.routers.apifox.scenario_schemas import ScenarioReorderItem
from app.services.apifox import scenario_service as service


def _scenario(db, project_id=1, name="s", folder_id=None, sort_order=0):
    s = ApifoxScenario(
        project_id=project_id, name=name, priority="medium", folder_id=folder_id, sort_order=sort_order
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _folder(db, project_id=1, name="f"):
    f = ApifoxFolder(project_id=project_id, name=name, kind="scenario")
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def _item(scenario_id, folder_id=None, sort_order=0):
    return ScenarioReorderItem(id=scenario_id, folder_id=folder_id, sort_order=sort_order)


# ---------- 组内重排 ----------
def test_reorder_within_group_updates_sort_order(db):
    a = _scenario(db, name="a", sort_order=0)
    b = _scenario(db, name="b", sort_order=1)
    c = _scenario(db, name="c", sort_order=2)

    # 拖成 c, a, b
    service.reorder_scenarios(db, 1, [_item(c.id, None, 0), _item(a.id, None, 1), _item(b.id, None, 2)])

    ordered = [s.name for s in repo.list_scenarios(db, 1)]
    assert ordered == ["c", "a", "b"]


# ---------- 跨组移动 ----------
def test_reorder_moves_scenario_into_folder(db):
    folder = _folder(db, name="分组1")
    s = _scenario(db, name="s", folder_id=None, sort_order=0)

    service.reorder_scenarios(db, 1, [_item(s.id, folder.id, 0)])

    db.refresh(s)
    assert s.folder_id == folder.id and s.sort_order == 0


def test_reorder_moves_scenario_to_ungrouped(db):
    folder = _folder(db)
    s = _scenario(db, name="s", folder_id=folder.id, sort_order=3)

    service.reorder_scenarios(db, 1, [_item(s.id, None, 0)])

    db.refresh(s)
    assert s.folder_id is None and s.sort_order == 0


def test_reorder_cross_group_two_groups_snapshot(db):
    folder = _folder(db, name="F")
    # 源组(未分组): a, b；目标组(F): x
    a = _scenario(db, name="a", folder_id=None, sort_order=0)
    b = _scenario(db, name="b", folder_id=None, sort_order=1)
    x = _scenario(db, name="x", folder_id=folder.id, sort_order=0)

    # 把 b 从未分组拖到 F 的首位：源组只剩 a(0)，目标组 b(0), x(1)
    service.reorder_scenarios(
        db, 1,
        [_item(a.id, None, 0), _item(b.id, folder.id, 0), _item(x.id, folder.id, 1)],
    )

    db.refresh(a)
    db.refresh(b)
    db.refresh(x)
    assert (a.folder_id, a.sort_order) == (None, 0)
    assert (b.folder_id, b.sort_order) == (folder.id, 0)
    assert (x.folder_id, x.sort_order) == (folder.id, 1)


# ---------- 只更新传入 id ----------
def test_reorder_only_touches_passed_ids(db):
    a = _scenario(db, name="a", sort_order=0)
    untouched = _scenario(db, name="untouched", folder_id=None, sort_order=5)

    service.reorder_scenarios(db, 1, [_item(a.id, None, 9)])

    db.refresh(untouched)
    assert untouched.sort_order == 5  # 未传入的场景不动


# ---------- 校验 ----------
def test_reorder_rejects_unknown_scenario(db):
    with pytest.raises(ValueError):
        service.reorder_scenarios(db, 1, [_item(99999, None, 0)])


def test_reorder_rejects_scenario_from_other_project(db):
    other = _scenario(db, project_id=2, name="other")

    with pytest.raises(ValueError):
        service.reorder_scenarios(db, 1, [_item(other.id, None, 0)])


def test_reorder_rejects_folder_from_other_project(db):
    foreign_folder = _folder(db, project_id=2)
    s = _scenario(db, project_id=1, name="s")

    with pytest.raises(ValueError):
        service.reorder_scenarios(db, 1, [_item(s.id, foreign_folder.id, 0)])


def test_reorder_does_not_bump_version(db):
    s = _scenario(db, name="s")
    v0 = s.version

    service.reorder_scenarios(db, 1, [_item(s.id, None, 1)])

    db.refresh(s)
    assert s.version == v0  # 排序不算内容编辑，不动乐观锁版本

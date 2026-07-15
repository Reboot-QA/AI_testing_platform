"""场景文件夹（复用 apifox_folders，kind='scenario'，单层）：CRUD / 移动 / 计数 / 与接口文件夹隔离。"""

import pytest

from app.models.apifox.endpoint import ApifoxFolder
from app.repositories.apifox import endpoint_repo, scenario_repo
from app.routers.apifox.scenario_schemas import ScenarioCreate, ScenarioUpdate
from app.services.apifox import scenario_folder_service as fsvc
from app.services.apifox import scenario_service as svc


def test_create_and_list_folder(db):
    folder = fsvc.create_folder(db, project_id=1, name="冒烟")

    assert folder.name == "冒烟"
    assert folder.scenario_count == 0
    assert [f.id for f in fsvc.list_folders(db, 1)] == [folder.id]


def test_create_scenario_in_folder(db):
    folder = fsvc.create_folder(db, 1, "冒烟")

    out = svc.create_scenario(db, 1, ScenarioCreate(name="S", folder_id=folder.id))

    assert out.folder_id == folder.id


def test_create_scenario_invalid_folder_raises(db):
    with pytest.raises(ValueError):
        svc.create_scenario(db, 1, ScenarioCreate(name="S", folder_id=999))


def test_update_moves_scenario_between_folder_and_ungrouped(db):
    folder = fsvc.create_folder(db, 1, "冒烟")
    created = svc.create_scenario(db, 1, ScenarioCreate(name="S"))
    scenario = scenario_repo.get_scenario(db, created.id)

    moved = svc.update_scenario(db, scenario, ScenarioUpdate(folder_id=folder.id))
    assert moved.folder_id == folder.id

    ungrouped = svc.update_scenario(db, scenario, ScenarioUpdate(folder_id=None))
    assert ungrouped.folder_id is None  # None 显式传入=移到未分组


def test_folder_count_reflects_scenarios(db):
    folder = fsvc.create_folder(db, 1, "冒烟")
    svc.create_scenario(db, 1, ScenarioCreate(name="A", folder_id=folder.id))
    svc.create_scenario(db, 1, ScenarioCreate(name="B", folder_id=folder.id))

    assert fsvc.list_folders(db, 1)[0].scenario_count == 2


def test_delete_folder_ungroups_scenarios_not_delete(db):
    folder = fsvc.create_folder(db, 1, "冒烟")
    created = svc.create_scenario(db, 1, ScenarioCreate(name="S", folder_id=folder.id))

    fsvc.delete_folder(db, scenario_repo.get_scenario_folder(db, folder.id))

    assert scenario_repo.get_scenario_folder(db, folder.id) is None
    assert scenario_repo.get_scenario(db, created.id).folder_id is None  # 场景保留，仅解组


def test_scenario_and_endpoint_folders_isolated_by_kind(db):
    sf = fsvc.create_folder(db, 1, "场景夹")
    ep = ApifoxFolder(project_id=1, name="接口夹", kind="endpoint")
    db.add(ep)
    db.commit()

    assert sf.id not in [f.id for f in endpoint_repo.list_folders(db, 1)]  # 场景夹不入接口树
    assert ep.id not in [f.id for f in fsvc.list_folders(db, 1)]  # 接口夹不入场景列表


def test_create_scenario_with_endpoint_folder_id_rejected(db):
    ep = ApifoxFolder(project_id=1, name="接口夹", kind="endpoint")
    db.add(ep)
    db.commit()

    with pytest.raises(ValueError):  # 场景只能挂 kind=scenario 的文件夹
        svc.create_scenario(db, 1, ScenarioCreate(name="S", folder_id=ep.id))


def test_update_scenario_to_endpoint_folder_rejected(db):
    ep = ApifoxFolder(project_id=1, name="接口夹", kind="endpoint")
    db.add(ep)
    db.commit()
    created = svc.create_scenario(db, 1, ScenarioCreate(name="S"))
    scenario = scenario_repo.get_scenario(db, created.id)

    with pytest.raises(ValueError):
        svc.update_scenario(db, scenario, ScenarioUpdate(folder_id=ep.id))

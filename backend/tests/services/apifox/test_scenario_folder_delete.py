"""删场景文件夹 → 其下场景级联软删进回收站（可还原），不再掉到未分组（Confluence 7/24-#13）。"""

from app.repositories.apifox import scenario_repo
from app.routers.apifox.scenario_schemas import ScenarioCreate
from app.services.apifox import scenario_folder_service, scenario_service


def test_delete_folder_cascades_soft_delete_to_scenarios(db):
    folder = scenario_folder_service.create_folder(db, project_id=1, name="F")
    out = scenario_service.create_scenario(
        db, project_id=1, data=ScenarioCreate(name="s", folder_id=folder.id)
    )
    assert scenario_repo.get_scenario(db, out.id).folder_id == folder.id

    fobj = scenario_repo.get_scenario_folder(db, folder.id)
    scenario_folder_service.delete_folder(db, fobj, deleted_by=7)

    # 文件夹已删；场景进回收站（软删、记删除人），不在活动列表、不落未分组
    assert scenario_repo.get_scenario_folder(db, folder.id) is None
    deleted_ids = [s.id for s in scenario_repo.list_deleted_scenarios(db, 1)]
    assert out.id in deleted_ids  # 修复前：场景 folder_id=None 仍在活动列表（未分组）
    active_ids = [s.id for s in scenario_repo.list_scenarios(db, 1)]
    assert out.id not in active_ids
    got = scenario_repo.get_scenario(db, out.id)
    assert got.deleted_at is not None and got.deleted_by == 7

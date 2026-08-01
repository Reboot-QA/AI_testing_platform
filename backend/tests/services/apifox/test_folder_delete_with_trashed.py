"""删文件夹时，回收站里仍挂在该文件夹下的条目必须一并解除 folder_id。

复现测试提的「删除文件夹提示服务器内部错误」：
delete_folder 只遍历未软删的接口/场景来置空 folder_id，回收站里的仍指向该文件夹，
线上 MySQL 删 apifox_folders 行时报
(1451, Cannot delete or update a parent row: a foreign key constraint fails
 (ai_testcase.apifox_endpoints, CONSTRAINT apifox_endpoints_ibfk_2 FOREIGN KEY (folder_id)))
路由只捕获 ValueError，落到 500。sqlite 不校验外键，故直接断言 folder_id 是否解除。
"""

from app.repositories.apifox import endpoint_repo, scenario_repo
from app.routers.apifox.scenario_schemas import ScenarioCreate
from app.routers.apifox.schemas import EndpointCreate, FolderCreate
from app.services.apifox import endpoint_service as svc
from app.services.apifox import scenario_folder_service, scenario_service


def test_delete_endpoint_folder_releases_trashed_endpoint(db):
    folder = svc.create_folder(db, 1, FolderCreate(name="导入的接口", parent_id=None))
    trashed = svc.create_endpoint(
        db, 1, EndpointCreate(name="旧接口", method="GET", path="/old", folder_id=folder.id)
    )
    kept = svc.create_endpoint(
        db, 1, EndpointCreate(name="新接口", method="POST", path="/new", folder_id=folder.id)
    )
    svc.delete_endpoint(db, endpoint_repo.get_endpoint(db, trashed.id))

    svc.delete_folder(db, endpoint_repo.get_folder(db, folder.id))

    assert endpoint_repo.get_folder(db, folder.id) is None
    assert endpoint_repo.get_endpoint(db, kept.id).folder_id is None
    assert endpoint_repo.get_endpoint(db, trashed.id).folder_id is None


def test_trashed_endpoint_keeps_its_delete_metadata(db):
    """解除 FK 不能顺手改掉原来的删除时间/操作人，否则回收站的「谁删的、何时删」会被篡改。"""
    folder = svc.create_folder(db, 1, FolderCreate(name="夹", parent_id=None))
    ep = svc.create_endpoint(
        db, 1, EndpointCreate(name="接口", method="GET", path="/a", folder_id=folder.id)
    )
    svc.delete_endpoint(db, endpoint_repo.get_endpoint(db, ep.id), deleted_by=7)
    deleted_at = endpoint_repo.get_endpoint(db, ep.id).deleted_at

    svc.delete_folder(db, endpoint_repo.get_folder(db, folder.id), deleted_by=9)

    trashed = endpoint_repo.get_endpoint(db, ep.id)
    assert trashed.deleted_at == deleted_at
    assert trashed.deleted_by == 7


def test_delete_scenario_folder_releases_trashed_scenario(db):
    folder = scenario_folder_service.create_folder(db, 1, "场景夹")
    trashed = scenario_service.create_scenario(
        db, 1, ScenarioCreate(name="旧场景", folder_id=folder.id, steps=[])
    )
    scenario_service.delete_scenario(db, scenario_repo.get_scenario(db, trashed.id))

    scenario_folder_service.delete_folder(db, scenario_repo.get_scenario_folder(db, folder.id))

    assert scenario_repo.get_scenario_folder(db, folder.id) is None
    assert scenario_repo.get_scenario(db, trashed.id).folder_id is None

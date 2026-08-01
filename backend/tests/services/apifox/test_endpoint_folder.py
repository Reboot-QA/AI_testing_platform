"""接口文件夹级联删除：子文件夹 + 其下接口软删除进回收站。"""

import pytest

from app.repositories.apifox import endpoint_repo
from app.routers.apifox.schemas import EndpointCreate, FolderCreate
from app.services.apifox import endpoint_service as svc


def test_delete_folder_cascades_endpoints_to_trash(db):
    parent = svc.create_folder(db, 1, FolderCreate(name="认证", parent_id=None))
    child = svc.create_folder(db, 1, FolderCreate(name="子夹", parent_id=parent.id))
    ep1 = svc.create_endpoint(
        db, 1, EndpointCreate(name="Login", method="POST", path="/login", folder_id=parent.id)
    )
    ep2 = svc.create_endpoint(
        db, 1, EndpointCreate(name="Me", method="GET", path="/me", folder_id=child.id)
    )

    folder = endpoint_repo.get_folder(db, parent.id)
    svc.delete_folder(db, folder)

    assert endpoint_repo.get_folder(db, parent.id) is None
    assert endpoint_repo.get_folder(db, child.id) is None
    assert endpoint_repo.get_endpoint(db, ep1.id).deleted_at is not None
    assert endpoint_repo.get_endpoint(db, ep2.id).deleted_at is not None
    assert endpoint_repo.get_endpoint(db, ep1.id).folder_id is None
    assert endpoint_repo.list_endpoints(db, 1) == []


def test_delete_nested_folders_under_sqlite_fk(db):
    """嵌套文件夹：SQLAlchemy 会把多行 DELETE 打成 executemany 且按 id 序（父先于子）。

    不开 FK 时（pytest 默认）测不出来；开启后若未先断开 parent_id，会 IntegrityError。
    """
    from sqlalchemy import text

    parent = svc.create_folder(db, 1, FolderCreate(name="父", parent_id=None))
    child = svc.create_folder(db, 1, FolderCreate(name="子", parent_id=parent.id))
    gchild = svc.create_folder(db, 1, FolderCreate(name="孙", parent_id=child.id))
    svc.create_endpoint(
        db, 1, EndpointCreate(name="e", method="GET", path="/x", folder_id=gchild.id)
    )

    try:
        db.execute(text("PRAGMA foreign_keys=ON"))
        assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1
        svc.delete_folder(db, endpoint_repo.get_folder(db, parent.id))
    finally:
        # 连接可能被池化复用，务必关回，避免污染同进程后续用例
        db.execute(text("PRAGMA foreign_keys=OFF"))

    assert endpoint_repo.get_folder(db, parent.id) is None
    assert endpoint_repo.get_folder(db, child.id) is None
    assert endpoint_repo.get_folder(db, gchild.id) is None
    assert endpoint_repo.list_endpoints(db, 1) == []


def test_delete_empty_folder_still_works(db):
    folder = svc.create_folder(db, 1, FolderCreate(name="空夹", parent_id=None))

    svc.delete_folder(db, endpoint_repo.get_folder(db, folder.id))

    assert endpoint_repo.list_folders(db, 1) == []


def test_delete_folder_blocked_when_case_referenced_by_scenario(db, make_case):
    from app.routers.apifox.scenario_schemas import ScenarioCreate, StepIn
    from app.services.apifox import scenario_service

    folder = svc.create_folder(db, 1, FolderCreate(name="认证", parent_id=None))
    ep = svc.create_endpoint(
        db, 1, EndpointCreate(name="Login", method="POST", path="/login", folder_id=folder.id)
    )
    case = make_case(endpoint=ep, name="登录成功")
    scenario_service.create_scenario(
        db,
        1,
        ScenarioCreate(name="登录流", steps=[StepIn(type="case", ref_case_id=case.id)]),
    )

    with pytest.raises(ValueError, match="场景步骤引用"):
        svc.delete_folder(db, endpoint_repo.get_folder(db, folder.id))

    assert endpoint_repo.get_folder(db, folder.id) is not None

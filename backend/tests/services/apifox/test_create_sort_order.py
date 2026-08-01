"""新建接口/文件夹/数据模型时排到同层末尾（最新在最下），不因默认 sort_order=0 跑到已拖拽层顶部。

复现：在已拖拽过的层（同层其它项 sort_order 已是 1,2…），旧逻辑新建项 sort_order=0 会插到最前。
"""

from app.repositories.apifox import endpoint_repo, schema_repo
from app.routers.apifox.data_model_schemas import SchemaCreate
from app.routers.apifox.schemas import EndpointCreate, FolderCreate
from app.services.apifox import endpoint_service as ep_svc
from app.services.apifox import schema_service as sc_svc


def _drag(objs, db):
    """模拟拖拽：把已有对象排成 sort_order 1,2,3…（都非默认 0）。"""
    for i, obj in enumerate(objs, start=1):
        obj.sort_order = i
    db.commit()


def test_new_endpoint_appended_to_folder_end(db):
    folder = ep_svc.create_folder(db, 1, FolderCreate(name="F", parent_id=None))
    a = ep_svc.create_endpoint(db, 1, EndpointCreate(name="a", method="GET", path="/a", folder_id=folder.id))
    b = ep_svc.create_endpoint(db, 1, EndpointCreate(name="b", method="GET", path="/b", folder_id=folder.id))
    _drag([endpoint_repo.get_endpoint(db, a.id), endpoint_repo.get_endpoint(db, b.id)], db)

    c = ep_svc.create_endpoint(db, 1, EndpointCreate(name="c", method="GET", path="/c", folder_id=folder.id))

    in_folder = [e.id for e in endpoint_repo.list_endpoints(db, 1) if e.folder_id == folder.id]
    assert in_folder[-1] == c.id  # 新建落到末尾，而非顶部


def test_new_endpoint_sort_order_scoped_per_folder(db):
    f1 = ep_svc.create_folder(db, 1, FolderCreate(name="F1", parent_id=None))
    f2 = ep_svc.create_folder(db, 1, FolderCreate(name="F2", parent_id=None))
    a = ep_svc.create_endpoint(db, 1, EndpointCreate(name="a", method="GET", path="/a", folder_id=f1.id))
    _drag([endpoint_repo.get_endpoint(db, a.id)], db)  # f1 里已有 sort_order=1

    # f2 为空，新建应从 0 起（不受 f1 的 max 影响）
    b = ep_svc.create_endpoint(db, 1, EndpointCreate(name="b", method="GET", path="/b", folder_id=f2.id))
    assert endpoint_repo.get_endpoint(db, b.id).sort_order == 0


def test_new_folder_appended_to_end(db):
    a = ep_svc.create_folder(db, 1, FolderCreate(name="a", parent_id=None))
    b = ep_svc.create_folder(db, 1, FolderCreate(name="b", parent_id=None))
    _drag([endpoint_repo.get_folder(db, a.id), endpoint_repo.get_folder(db, b.id)], db)

    c = ep_svc.create_folder(db, 1, FolderCreate(name="c", parent_id=None))

    root_ids = [f.id for f in endpoint_repo.list_folders(db, 1) if f.parent_id is None]
    assert root_ids[-1] == c.id


def test_new_schema_appended_to_end(db):
    a = sc_svc.create_schema(db, 1, SchemaCreate(name="A", json_schema='{"type":"object"}'))
    b = sc_svc.create_schema(db, 1, SchemaCreate(name="B", json_schema='{"type":"object"}'))
    _drag([schema_repo.get_schema(db, a.id), schema_repo.get_schema(db, b.id)], db)

    c = sc_svc.create_schema(db, 1, SchemaCreate(name="C", json_schema='{"type":"object"}'))

    ids = [s.id for s in schema_repo.list_schemas(db, 1)]
    assert ids[-1] == c.id

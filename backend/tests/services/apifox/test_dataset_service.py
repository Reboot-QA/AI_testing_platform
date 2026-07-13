"""项目级数据集 · CRUD + bulk 行替换 + 引用计数 / 删除保护。

被测：app/services/apifox/dataset_service.py。仅业务逻辑，sqlite 隔离库。
"""

import json

import pytest

from app.models.apifox.case import ApifoxEndpointCase
from app.repositories.apifox import dataset_repo
from app.routers.apifox.dataset_schemas import DatasetCreate, DatasetRowIn, DatasetUpdate
from app.services.apifox import dataset_service as svc


def _create(db, name="ds", columns=None, rows=None, project_id=1):
    return svc.create_dataset(
        db, project_id, DatasetCreate(name=name, columns=columns or ["user"], rows=rows or [])
    )


def _get(db, did):
    return dataset_repo.get_dataset(db, did)


def _bind_case(db, dataset_id, project_id=1):
    case = ApifoxEndpointCase(
        project_id=project_id, endpoint_id=1, name="c",
        data_drive=json.dumps({"enabled": True, "source": "dataset", "dataset_id": dataset_id}),
    )
    db.add(case)
    db.commit()


def test_create_with_rows_persists_ordered(db):
    out = _create(db, rows=[DatasetRowIn(values={"user": "a"}), DatasetRowIn(values={"user": "b"})])

    assert [r.values["user"] for r in out.rows] == ["a", "b"]


def test_create_duplicate_name_rejected(db):
    _create(db, name="dup")

    with pytest.raises(ValueError, match="已存在"):
        _create(db, name="dup")


def test_update_replaces_rows(db):
    out = _create(db, rows=[DatasetRowIn(values={"user": "a"})])
    ds = _get(db, out.id)

    updated = svc.update_dataset(
        db, ds, DatasetUpdate(rows=[DatasetRowIn(values={"user": "x"}), DatasetRowIn(values={"user": "y"})])
    )

    assert [r.values["user"] for r in updated.rows] == ["x", "y"]


def test_update_columns(db):
    out = _create(db, columns=["a"])
    ds = _get(db, out.id)

    updated = svc.update_dataset(db, ds, DatasetUpdate(columns=["a", "b"]))

    assert updated.columns == ["a", "b"]


def test_delete_unreferenced_ok(db):
    out = _create(db, name="free")

    svc.delete_dataset(db, _get(db, out.id))

    assert _get(db, out.id) is None


def test_delete_referenced_by_case_rejected(db):
    out = _create(db, name="used")
    _bind_case(db, out.id)

    with pytest.raises(ValueError, match="用例"):
        svc.delete_dataset(db, _get(db, out.id))


def test_ref_count_reflects_referencing_cases(db):
    out = _create(db, name="counted")
    _bind_case(db, out.id)
    _bind_case(db, out.id)

    brief = next(b for b in svc.list_datasets(db, 1) if b.id == out.id)

    assert brief.ref_count == 2


def test_brief_row_and_column_counts(db):
    out = _create(
        db, columns=["a", "b"],
        rows=[DatasetRowIn(values={"a": "1"}), DatasetRowIn(values={"a": "2"})],
    )

    brief = next(b for b in svc.list_datasets(db, 1) if b.id == out.id)

    assert brief.column_count == 2
    assert brief.row_count == 2

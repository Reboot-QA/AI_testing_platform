"""G1 乐观锁扩展 · 脚本/数据模型/数据集保存冲突检测。

被测：script_service / schema_service / dataset_service 的 update_* version 校验与自增。
三实体走同一 versioning.bump_version（DB 级原子 CAS），此处按实体各覆盖
匹配自增 / 陈旧冲突 / 无版本向后兼容 三条不变量。
"""

import pytest

from app.repositories.apifox import dataset_repo, schema_repo, script_repo
from app.routers.apifox.data_model_schemas import SchemaCreate, SchemaUpdate
from app.routers.apifox.dataset_schemas import DatasetCreate, DatasetUpdate
from app.routers.apifox.script_schemas import ScriptCreate, ScriptUpdate
from app.services.apifox import dataset_service, schema_service, script_service
from app.services.apifox.errors import ConflictError


# ---------- 脚本 ----------
def _script(db):
    out = script_service.create_script(db, 1, ScriptCreate(name="s"))
    return script_repo.get_script(db, out.id)


def test_script_matching_version_increments(db):
    script = _script(db)
    assert script.version == 1

    out = script_service.update_script(db, script, ScriptUpdate(name="s2", expected_version=1))

    assert out.version == 2


def test_script_stale_version_raises_conflict(db):
    script = _script(db)
    script_service.update_script(db, script, ScriptUpdate(name="s2", expected_version=1))  # → v2

    with pytest.raises(ConflictError) as ei:
        script_service.update_script(db, script, ScriptUpdate(name="s3", expected_version=1))

    assert ei.value.current_version == 2


def test_script_without_version_backward_compat(db):
    script = _script(db)

    out = script_service.update_script(db, script, ScriptUpdate(name="s2"))

    assert out.version == 2


# ---------- 数据模型 ----------
def _schema(db):
    out = schema_service.create_schema(db, 1, SchemaCreate(name="m"))
    return schema_repo.get_schema(db, out.id)


def test_schema_matching_version_increments(db):
    schema = _schema(db)
    assert schema.version == 1

    out = schema_service.update_schema(db, schema, SchemaUpdate(name="m2", expected_version=1))

    assert out.version == 2


def test_schema_stale_version_raises_conflict(db):
    schema = _schema(db)
    schema_service.update_schema(db, schema, SchemaUpdate(name="m2", expected_version=1))  # → v2

    with pytest.raises(ConflictError) as ei:
        schema_service.update_schema(db, schema, SchemaUpdate(name="m3", expected_version=1))

    assert ei.value.current_version == 2


def test_schema_without_version_backward_compat(db):
    schema = _schema(db)

    out = schema_service.update_schema(db, schema, SchemaUpdate(name="m2"))

    assert out.version == 2


# ---------- 数据集 ----------
def _dataset(db):
    out = dataset_service.create_dataset(db, 1, DatasetCreate(name="d", columns=["c"]))
    return dataset_repo.get_dataset(db, out.id)


def test_dataset_matching_version_increments(db):
    dataset = _dataset(db)
    assert dataset.version == 1

    out = dataset_service.update_dataset(db, dataset, DatasetUpdate(name="d2", expected_version=1))

    assert out.version == 2


def test_dataset_stale_version_raises_conflict(db):
    dataset = _dataset(db)
    dataset_service.update_dataset(db, dataset, DatasetUpdate(name="d2", expected_version=1))  # → v2

    with pytest.raises(ConflictError) as ei:
        dataset_service.update_dataset(db, dataset, DatasetUpdate(name="d3", expected_version=1))

    assert ei.value.current_version == 2


def test_dataset_without_version_backward_compat(db):
    dataset = _dataset(db)

    out = dataset_service.update_dataset(db, dataset, DatasetUpdate(name="d2"))

    assert out.version == 2


def test_dataset_conflict_does_not_mutate(db):
    dataset = _dataset(db)
    dataset_service.update_dataset(db, dataset, DatasetUpdate(name="d2", expected_version=1))  # → v2

    with pytest.raises(ConflictError):
        dataset_service.update_dataset(db, dataset, DatasetUpdate(name="nope", expected_version=1))

    assert dataset_repo.get_dataset(db, dataset.id).name == "d2"  # 冲突不落改动

"""更新 Swagger / 导入 · components.schemas 大小写不敏感去重（对齐 MySQL 唯一索引 ci）。

回归：MySQL 唯一索引 (project_id, name) 大小写不敏感，而旧去重区分大小写，
导致同名仅大小写不同的 schema 触发 Duplicate entry → apply_sync 500。
"""

from app.models.apifox.data_model import ApifoxSchema
from app.repositories.apifox import schema_repo
from app.services.apifox import import_service as svc

PID = 1


def _doc(schema_names):
    return {
        "openapi": "3.0.0",
        "paths": {"/x": {"get": {"responses": {}}}},
        "components": {"schemas": {n: {"type": "object"} for n in schema_names}},
    }


def _existing_schema(db, name):
    schema_repo.add(db, ApifoxSchema(project_id=PID, name=name, json_schema="{}"))
    db.commit()


def test_import_schemas_skips_case_insensitive_existing(db):
    _existing_schema(db, "AiGenerateRequest")

    created = svc.import_schemas(db, PID, _doc(["aigeneraterequest"]))

    assert created == 0  # 大小写不同视为同名，跳过（否则撞 MySQL ci 唯一索引）
    assert db.query(ApifoxSchema).filter_by(project_id=PID).count() == 1


def test_import_schemas_dedups_case_variants_within_doc(db):
    created = svc.import_schemas(db, PID, _doc(["Foo", "foo"]))

    assert created == 1
    assert db.query(ApifoxSchema).filter_by(project_id=PID).count() == 1


def test_import_schemas_creates_distinct_names(db):
    created = svc.import_schemas(db, PID, _doc(["Foo", "Bar"]))

    assert created == 2


def test_count_new_schemas_case_insensitive(db):
    _existing_schema(db, "AiGenerateRequest")

    # 预览计数应与 import 实际新建一致：大小写变体不计入新增
    count = svc.count_new_schemas(db, PID, _doc(["aigeneraterequest", "New"]))

    assert count == 1

"""apply_sync 全链路：库里已有同名 schema 时再次同步不应撞唯一约束（复现用户报的 500）。"""

from app.models.apifox.data_model import ApifoxSchema
from app.repositories.apifox import schema_repo
from app.services.apifox import import_sync_service as sync

PID = 1


def _doc(schema_names):
    return {
        "openapi": "3.0.0",
        "paths": {"/x": {"get": {"responses": {}}}},
        "components": {"schemas": {n: {"type": "object"} for n in schema_names}},
    }


def test_apply_sync_with_existing_same_name_schema_no_duplicate(db):
    schema_repo.add(db, ApifoxSchema(project_id=PID, name="AiGenerateRequest", json_schema="{}"))
    db.commit()

    # 再次同步含同名 schema 的文档 —— 不应抛 IntegrityError
    report = sync.apply_sync(db, PID, _doc(["AiGenerateRequest", "NewModel"]), False)

    assert report.schemas_created == 1  # 只新建 NewModel，AiGenerateRequest 跳过
    got = [s.name for s in schema_repo.list_schemas(db, PID)]
    assert sorted(got) == ["AiGenerateRequest", "NewModel"]


def test_apply_sync_case_variant_schema_in_doc_no_duplicate(db):
    # 文档里同时出现大小写变体（模拟平台自身 openapi 里潜在的重名）
    report = sync.apply_sync(db, PID, _doc(["Foo", "foo", "FOO"]), False)

    assert report.schemas_created == 1
    assert len(schema_repo.list_schemas(db, PID)) == 1

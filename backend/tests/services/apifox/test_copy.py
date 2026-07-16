"""apifox 套件/用例复制（M4 迁移）：深拷子表 + 名称去重。"""

from app.models.apifox.script import ApifoxScript
from app.repositories.apifox import case_repo, suite_repo
from app.routers.apifox.case_schemas import AssertionRow, CaseCreate, CaseScriptRef, ExtractRow
from app.routers.apifox.suite_schemas import SuiteCreate, SuiteItemIn
from app.services.apifox import case_service, suite_service


def test_copy_case_duplicates_case_and_children(db, make_endpoint):
    ep = make_endpoint()
    script = ApifoxScript(project_id=ep.project_id, name="前置", lang="javascript", content="")
    db.add(script)
    db.commit()
    created = case_service.create_case(db, ep.project_id, ep.id, CaseCreate(
        name="登录", category="positive",
        assertions=[AssertionRow(type="status_code", operator="eq", expected="200")],
        extracts=[ExtractRow(var_name="tok", source="response_json", path="token")],
        pre_scripts=[CaseScriptRef(script_id=script.id)],
    ))
    case = case_repo.get_case(db, created.id)

    copied = case_service.copy_case(db, case)

    assert copied.id != created.id
    assert copied.name == "登录 副本"
    assert copied.category == "positive"
    assert [a.expected for a in copied.assertions] == ["200"]
    assert [e.var_name for e in copied.extracts] == ["tok"]
    assert [s.script_id for s in copied.pre_scripts] == [script.id]  # 前后置脚本引用也拷贝


def test_copy_case_name_increments_on_conflict(db, make_endpoint):
    ep = make_endpoint()
    created = case_service.create_case(db, ep.project_id, ep.id, CaseCreate(name="X"))
    case = case_repo.get_case(db, created.id)

    first = case_service.copy_case(db, case)
    second = case_service.copy_case(db, case)

    assert first.name == "X 副本"
    assert second.name == "X 副本2"


def test_copy_suite_duplicates_items(db, make_case):
    ca = make_case(name="A")
    cb = make_case(name="B")
    created = suite_service.create_suite(db, 1, SuiteCreate(name="冒烟", items=[
        SuiteItemIn(target_type="case", target_id=ca.id),
        SuiteItemIn(target_type="case", target_id=cb.id),
    ]))
    suite = suite_repo.get_suite(db, created.id)

    copied = suite_service.copy_suite(db, suite)

    assert copied.id != created.id
    assert copied.name == "冒烟 副本"
    assert [i.target_id for i in copied.items] == [ca.id, cb.id]

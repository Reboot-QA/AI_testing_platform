from app.constants.limits import REQ_CASE_TITLE_MAX_LEN
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User
from app.services.testcase_io_service import (
    build_testcases_import_template_excel,
    build_testcases_import_template_xmind,
    import_testcases_from_rows,
    parse_testcase_import_file,
)


def _seed_project(db, user: User) -> Project:
    project = Project(name="用例导入测试项目", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _seed_user(db, username: str = "case_importer") -> User:
    user = User(username=username, hashed_password="hashed", role="tester")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_import_testcases_append_allows_duplicate_titles(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    db.add(
        TestCase(
            project_id=project.id,
            title="已有用例",
            case_type="functional",
            priority="P1",
            review_status="approved",
            source="manual",
            created_by_id=user.id,
        )
    )
    db.commit()

    created, skipped, cleared = import_testcases_from_rows(
        db,
        project,
        [
            {"标题": "已有用例", "类型": "功能", "优先级": "P2", "来源": "手动", "评审状态": "已通过"},
            {"标题": "新用例", "类型": "功能", "优先级": "P1", "来源": "手动", "评审状态": "草稿"},
        ],
        user,
        mode="append",
    )

    assert created == 2
    assert skipped == 0
    assert cleared == 0

    cases = (
        db.query(TestCase)
        .filter(TestCase.project_id == project.id, TestCase.title == "已有用例")
        .order_by(TestCase.id.asc())
        .all()
    )
    assert len(cases) == 2
    assert cases[0].priority == "P1"
    assert cases[1].priority == "P2"


def test_import_testcases_replace_clears_and_imports(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    db.add(
        TestCase(
            project_id=project.id,
            title="旧用例",
            case_type="functional",
            priority="P1",
            review_status="approved",
            source="manual",
            created_by_id=user.id,
        )
    )
    db.commit()

    created, skipped, cleared = import_testcases_from_rows(
        db,
        project,
        [{"标题": "新用例A", "类型": "功能", "优先级": "P1", "来源": "手动", "评审状态": "待评审"}],
        user,
        mode="replace",
    )

    assert created == 1
    assert skipped == 0
    assert cleared == 1
    titles = [case.title for case in db.query(TestCase).filter(TestCase.project_id == project.id).all()]
    assert titles == ["新用例A"]


def test_testcase_import_templates_parse():
    xbuf, _ = build_testcases_import_template_excel()
    rows = parse_testcase_import_file("template.xlsx", xbuf.getvalue())
    assert len(rows) == 1
    assert rows[0]["标题"] == "示例用例"

    zbuf, _ = build_testcases_import_template_xmind()
    xrows = parse_testcase_import_file("template.xmind", zbuf.getvalue())
    assert len(xrows) == 1
    assert xrows[0]["标题"] == "示例用例"
    assert xrows[0]["需求点"] == "示例需求点"


def test_import_testcases_truncates_long_title_and_requirement_ref(db):
    user = _seed_user(db, "case_trunc_importer")
    project = _seed_project(db, user)
    long_req_title = "需" * (REQ_CASE_TITLE_MAX_LEN + 10)
    db.add(
        Requirement(
            project_id=project.id,
            title=long_req_title,
            req_type="functional",
            priority="P1",
            status="approved",
            source="manual",
            created_by_id=user.id,
        )
    )
    db.commit()

    long_case_title = "例" * (REQ_CASE_TITLE_MAX_LEN + 8)
    created, skipped, cleared = import_testcases_from_rows(
        db,
        project,
        [
            {
                "标题": long_case_title,
                "需求点": long_req_title,
                "类型": "功能",
                "优先级": "P1",
                "来源": "手动",
                "评审状态": "草稿",
            }
        ],
        user,
        mode="append",
    )

    assert created == 1
    assert skipped == 0
    assert cleared == 0

    case = db.query(TestCase).filter(TestCase.project_id == project.id).one()
    assert case.title == long_case_title[:REQ_CASE_TITLE_MAX_LEN]
    assert case.requirement_id is not None

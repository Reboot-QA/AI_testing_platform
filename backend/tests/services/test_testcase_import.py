from app.models.project import Project
from app.models.testcase import TestCase
from app.models.user import User
from app.services.testcase_io_service import import_testcases_from_rows


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

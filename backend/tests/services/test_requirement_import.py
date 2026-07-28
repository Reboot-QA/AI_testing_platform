from io import BytesIO

from openpyxl import Workbook

from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User
from app.services.requirement_io_service import (
    clear_project_requirements,
    import_requirements_from_rows,
    parse_requirement_import_file,
    summarize_import_rows,
)


def _seed_project(db, user: User) -> Project:
    project = Project(name="导入测试项目", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _seed_user(db, username: str = "importer") -> User:
    user = User(username=username, hashed_password="hashed", role="tester")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _build_excel_bytes(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def test_parse_excel_preserves_status_from_file():
    file_bytes = _build_excel_bytes(
        [
            ["序号", "标题", "类型", "优先级", "状态", "来源", "描述"],
            [1, "登录功能", "功能", "P1", "已评审", "文档解析", "支持账号登录"],
        ]
    )

    rows = parse_requirement_import_file("requirements.xlsx", file_bytes)

    assert len(rows) == 1
    assert rows[0]["状态"] == "已评审"


def test_summarize_import_rows_counts_all_valid_rows():
    rows = [
        {"标题": "A"},
        {"标题": "B"},
        {"标题": "A"},
    ]

    total_rows, unique_count, duplicate_merged, duplicate_titles = summarize_import_rows(rows)

    assert total_rows == 3
    assert unique_count == 3
    assert duplicate_merged == 0
    assert duplicate_titles == []


def test_import_requirements_append_imports_every_row(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    db.add(
        Requirement(
            project_id=project.id,
            title="已有需求",
            description="旧描述",
            req_type="functional",
            priority="P1",
            status="draft",
            source="manual",
            created_by_id=user.id,
        )
    )
    db.commit()

    created, skipped, cleared = import_requirements_from_rows(
        db,
        project,
        [
            {
                "序号": "2",
                "标题": "已有需求",
                "类型": "性能",
                "优先级": "P2",
                "状态": "已评审",
                "来源": "文档解析",
                "描述": "新描述",
            },
            {"序号": "3", "标题": "新需求", "类型": "功能", "优先级": "P1", "状态": "草稿", "来源": "手动", "描述": ""},
            {"序号": "4", "标题": "新需求", "类型": "功能", "优先级": "P2", "状态": "已评审", "来源": "手动", "描述": "第二行"},
        ],
        user,
        mode="append",
    )

    assert created == 3
    assert skipped == 0
    assert cleared == 0

    existing = db.query(Requirement).filter(Requirement.title == "已有需求").all()
    assert len(existing) == 2
    assert existing[0].description == "旧描述"

    new_rows = (
        db.query(Requirement)
        .filter(Requirement.title == "新需求")
        .order_by(Requirement.sort_order.asc())
        .all()
    )
    assert len(new_rows) == 2
    assert [row.sort_order for row in new_rows] == [3, 4]


def test_import_requirements_replace_clears_and_imports(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    db.add(
        Requirement(
            project_id=project.id,
            title="旧需求",
            req_type="functional",
            priority="P1",
            status="draft",
            source="manual",
            created_by_id=user.id,
        )
    )
    db.commit()

    created, skipped, cleared = import_requirements_from_rows(
        db,
        project,
        [{"标题": "新需求A", "类型": "功能", "优先级": "P1", "状态": "已评审", "来源": "文档解析", "描述": ""}],
        user,
        mode="replace",
    )

    assert created == 1
    assert skipped == 0
    assert cleared == 1
    titles = [req.title for req in db.query(Requirement).filter(Requirement.project_id == project.id).all()]
    assert titles == ["新需求A"]


def test_clear_project_requirements_unlinks_testcases(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    req = Requirement(
        project_id=project.id,
        title="待清空",
        req_type="functional",
        priority="P1",
        status="draft",
        source="manual",
        created_by_id=user.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    case = TestCase(
        project_id=project.id,
        title="关联用例",
        case_type="functional",
        priority="P1",
        requirement_id=req.id,
        created_by_id=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    cleared = clear_project_requirements(db, project.id)
    db.commit()

    assert cleared == 1
    db.refresh(case)
    assert case.requirement_id is None


def test_import_requirements_replace_preserves_excel_sort_order(db):
    user = _seed_user(db)
    project = _seed_project(db, user)

    created, skipped, cleared = import_requirements_from_rows(
        db,
        project,
        [
            {"序号": "31", "标题": "需求A", "类型": "功能", "优先级": "P1", "状态": "已评审", "来源": "文档解析", "描述": ""},
            {"序号": "40", "标题": "需求B", "类型": "功能", "优先级": "P1", "状态": "已评审", "来源": "文档解析", "描述": ""},
        ],
        user,
        mode="replace",
    )

    assert created == 2
    rows = (
        db.query(Requirement)
        .filter(Requirement.project_id == project.id)
        .order_by(Requirement.sort_order.asc())
        .all()
    )
    assert [row.sort_order for row in rows] == [31, 40]
    assert [row.title for row in rows] == ["需求A", "需求B"]


def test_import_requirements_imports_duplicate_titles_without_merge(db):
    user = _seed_user(db)
    project = _seed_project(db, user)

    created, skipped, cleared = import_requirements_from_rows(
        db,
        project,
        [
            {"序号": "1", "标题": "重复标题", "类型": "功能", "优先级": "P1", "状态": "已评审", "来源": "文档解析", "描述": "第一行"},
            {"序号": "2", "标题": "重复标题", "类型": "功能", "优先级": "P2", "状态": "已评审", "来源": "文档解析", "描述": "第二行"},
        ],
        user,
        mode="replace",
    )

    assert created == 2
    rows = (
        db.query(Requirement)
        .filter(Requirement.project_id == project.id)
        .order_by(Requirement.sort_order.asc())
        .all()
    )
    assert len(rows) == 2
    assert rows[0].description == "第一行"
    assert rows[1].description == "第二行"


def test_import_requirements_applies_excel_status(db):
    user = _seed_user(db)
    project = _seed_project(db, user)

    created, skipped, cleared = import_requirements_from_rows(
        db,
        project,
        [{"标题": "评审需求", "类型": "功能", "优先级": "P1", "状态": "已评审", "来源": "文档解析", "描述": ""}],
        user,
    )

    assert created == 1
    assert skipped == 0
    assert cleared == 0
    req = db.query(Requirement).filter(Requirement.project_id == project.id).one()
    assert req.status == "approved"

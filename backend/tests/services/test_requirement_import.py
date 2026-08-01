from io import BytesIO

from openpyxl import Workbook

from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User
from app.services.requirement_io_service import (
    build_requirements_import_template_excel,
    build_requirements_import_template_xmind,
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

    created, skipped, cleared, protected = import_requirements_from_rows(
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
    assert protected == 0

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
    assert [row.sort_order for row in new_rows] == [2, 3]


def test_import_requirements_append_ignores_excel_sort_order(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    db.add(
        Requirement(
            project_id=project.id,
            title="已有需求",
            sort_order=1,
            req_type="functional",
            priority="P1",
            status="draft",
            source="manual",
            created_by_id=user.id,
        )
    )
    db.commit()

    created, skipped, cleared, protected = import_requirements_from_rows(
        db,
        project,
        [
            {
                "序号": "1",
                "标题": "示例需求",
                "类型": "功能",
                "优先级": "P1",
                "状态": "草稿",
                "来源": "手动",
                "描述": "模板行",
            },
        ],
        user,
        mode="append",
    )

    assert created == 1
    imported = (
        db.query(Requirement)
        .filter(Requirement.project_id == project.id, Requirement.title == "示例需求")
        .one()
    )
    assert imported.sort_order == 2


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

    created, skipped, cleared, protected = import_requirements_from_rows(
        db,
        project,
        [{"标题": "新需求A", "类型": "功能", "优先级": "P1", "状态": "已评审", "来源": "文档解析", "描述": ""}],
        user,
        mode="replace",
    )

    assert created == 1
    assert skipped == 0
    assert cleared == 1
    assert protected == 0
    titles = [req.title for req in db.query(Requirement).filter(Requirement.project_id == project.id).all()]
    assert titles == ["新需求A"]


def test_clear_project_requirements_only_deletes_without_testcases(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    deletable = Requirement(
        project_id=project.id,
        title="可删除",
        req_type="functional",
        priority="P1",
        status="draft",
        source="manual",
        created_by_id=user.id,
    )
    protected_req = Requirement(
        project_id=project.id,
        title="保留",
        req_type="functional",
        priority="P1",
        status="draft",
        source="manual",
        created_by_id=user.id,
    )
    db.add_all([deletable, protected_req])
    db.commit()
    db.refresh(protected_req)
    case = TestCase(
        project_id=project.id,
        title="关联用例",
        case_type="functional",
        priority="P1",
        requirement_id=protected_req.id,
        created_by_id=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    deleted, protected = clear_project_requirements(db, project.id)
    db.commit()

    assert deleted == 1
    assert protected == 1
    db.refresh(case)
    assert case.requirement_id == protected_req.id
    remaining = db.query(Requirement).filter(Requirement.project_id == project.id).all()
    assert len(remaining) == 1
    assert remaining[0].title == "保留"


def test_import_requirements_replace_preserves_requirements_with_testcases(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    protected_req = Requirement(
        project_id=project.id,
        title="有用例的需求",
        sort_order=1,
        req_type="functional",
        priority="P1",
        status="draft",
        source="manual",
        created_by_id=user.id,
    )
    deletable_req = Requirement(
        project_id=project.id,
        title="旧需求",
        req_type="functional",
        priority="P1",
        status="draft",
        source="manual",
        created_by_id=user.id,
    )
    db.add_all([protected_req, deletable_req])
    db.commit()
    db.refresh(protected_req)
    db.add(
        TestCase(
            project_id=project.id,
            title="关联用例",
            case_type="functional",
            priority="P1",
            requirement_id=protected_req.id,
            created_by_id=user.id,
        )
    )
    db.commit()

    created, skipped, cleared, protected = import_requirements_from_rows(
        db,
        project,
        [{"标题": "新需求A", "类型": "功能", "优先级": "P1", "状态": "已评审", "来源": "文档解析", "描述": ""}],
        user,
        mode="replace",
    )

    assert created == 1
    assert skipped == 0
    assert cleared == 1
    assert protected == 1
    titles = sorted(req.title for req in db.query(Requirement).filter(Requirement.project_id == project.id).all())
    assert titles == ["新需求A", "有用例的需求"]
    imported = db.query(Requirement).filter(Requirement.title == "新需求A").one()
    assert imported.sort_order == 2


def test_import_requirements_replace_avoids_duplicate_sort_order_with_protected(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    protected_req = Requirement(
        project_id=project.id,
        title="AI 使用规范制定",
        sort_order=1,
        req_type="functional",
        priority="P1",
        status="approved",
        source="ai_document",
        created_by_id=user.id,
    )
    db.add(protected_req)
    db.commit()
    db.refresh(protected_req)
    db.add(
        TestCase(
            project_id=project.id,
            title="关联用例",
            case_type="functional",
            priority="P1",
            requirement_id=protected_req.id,
            created_by_id=user.id,
        )
    )
    db.commit()

    created, skipped, cleared, protected = import_requirements_from_rows(
        db,
        project,
        [
            {"序号": "1", "标题": "示例需求", "类型": "功能", "优先级": "P1", "状态": "草稿", "来源": "手动", "描述": ""},
            {"序号": "2", "标题": "需求B", "类型": "功能", "优先级": "P1", "状态": "草稿", "来源": "手动", "描述": ""},
        ],
        user,
        mode="replace",
    )

    assert created == 2
    assert protected == 1
    orders = {
        req.title: req.sort_order
        for req in db.query(Requirement).filter(Requirement.project_id == project.id).all()
    }
    assert orders["AI 使用规范制定"] == 1
    assert orders["示例需求"] == 2
    assert orders["需求B"] == 3
    assert len(set(orders.values())) == 3


def test_import_requirements_replace_preserves_excel_sort_order(db):
    user = _seed_user(db)
    project = _seed_project(db, user)

    created, skipped, cleared, protected = import_requirements_from_rows(
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

    created, skipped, cleared, protected = import_requirements_from_rows(
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

    created, skipped, cleared, protected = import_requirements_from_rows(
        db,
        project,
        [{"标题": "评审需求", "类型": "功能", "优先级": "P1", "状态": "已评审", "来源": "文档解析", "描述": ""}],
        user,
    )

    assert created == 1
    assert skipped == 0
    assert cleared == 0
    assert protected == 0
    req = db.query(Requirement).filter(Requirement.project_id == project.id).one()
    assert req.status == "approved"


def test_import_template_excel_and_xmind_parse():
    xbuf, _ = build_requirements_import_template_excel()
    rows = parse_requirement_import_file("template.xlsx", xbuf.getvalue())
    assert len(rows) >= 1
    assert rows[0]["标题"] == "示例需求"

    zbuf, _ = build_requirements_import_template_xmind()
    xrows = parse_requirement_import_file("template.xmind", zbuf.getvalue())
    assert len(xrows) == 2
    assert xrows[0]["标题"] == "示例需求一"
    assert xrows[0]["优先级"] == "P1"

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase
from app.models.user import User
from app.routers.projects import requirements_overview
from app.routers.requirements import list_requirements
from app.services.overview_service import get_requirements_overview


def _seed_user(db, username: str = "req_tester") -> User:
    user = User(username=username, hashed_password="hashed", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_project(db, user: User) -> Project:
    project = Project(name="需求概览项目", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_requirements_overview_counts(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    linked_req = Requirement(
        project_id=project.id, title="已关联", status="approved", source="manual"
    )
    ai_req = Requirement(
        project_id=project.id, title="AI未评审", status="draft", source="ai_document"
    )
    unlinked = Requirement(
        project_id=project.id, title="未覆盖", status="approved", source="manual"
    )
    db.add_all([linked_req, ai_req, unlinked])
    db.flush()
    db.add(
        TestCase(
            project_id=project.id,
            requirement_id=linked_req.id,
            title="关联用例",
            source="manual",
            review_status="approved",
        )
    )
    db.commit()

    out = get_requirements_overview(db, project.id)
    assert out["req_total"] == 3
    assert out["unreviewed_count"] == 1
    assert out["linked_count"] == 1
    assert out["unlinked_count"] == 2
    assert out["ai_document_count"] == 1
    assert out["ai_unreviewed_count"] == 1

    api_out = requirements_overview(project.id, db, user)
    assert api_out["linked_count"] == 1


def test_list_requirements_source_order_and_linked(db):
    user = _seed_user(db, "req_filter")
    project = _seed_project(db, user)
    older = datetime.utcnow() - timedelta(days=1)
    newer = datetime.utcnow()
    r_old = Requirement(
        project_id=project.id,
        title="旧AI",
        status="draft",
        source="ai_document",
        created_at=older,
    )
    r_new = Requirement(
        project_id=project.id,
        title="新AI",
        status="draft",
        source="ai_document",
        created_at=newer,
    )
    r_manual = Requirement(
        project_id=project.id,
        title="手动",
        status="approved",
        source="manual",
        created_at=newer,
    )
    db.add_all([r_old, r_new, r_manual])
    db.flush()
    db.add(
        TestCase(
            project_id=project.id,
            requirement_id=r_manual.id,
            title="c1",
            source="manual",
            review_status="approved",
        )
    )
    db.commit()

    page = list_requirements(
        project_id=project.id,
        status=None,
        source="ai_document",
        order="created_at_desc",
        unreviewed=None,
        linked=None,
        keyword=None,
        page=1,
        page_size=10,
        db=db,
        current_user=user,
    )
    assert page.total == 2
    assert [item.title for item in page.items] == ["新AI", "旧AI"]

    unlinked_page = list_requirements(
        project_id=project.id,
        status=None,
        source=None,
        order=None,
        unreviewed=None,
        linked=False,
        keyword=None,
        page=1,
        page_size=10,
        db=db,
        current_user=user,
    )
    assert unlinked_page.total == 2

    with pytest.raises(HTTPException) as exc:
        list_requirements(
            project_id=project.id,
            status=None,
            source="bad",
            order=None,
            unreviewed=None,
            linked=None,
            keyword=None,
            page=1,
            page_size=10,
            db=db,
            current_user=user,
        )
    assert exc.value.status_code == 400

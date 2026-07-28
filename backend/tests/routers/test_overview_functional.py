from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models.project import Project
from app.models.requirement import Requirement
from app.models.test_execution import ManualTestRun
from app.models.testcase import TestCase
from app.models.user import User
from app.routers.projects import functional_overview
from app.routers.testcases import list_testcases
from app.services.overview_service import get_functional_overview


def _seed_user(db, username: str = "tester") -> User:
    user = User(username=username, hashed_password="hashed", role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_project(db, user: User) -> Project:
    project = Project(name="概览测试项目", owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_functional_overview_counts(db):
    user = _seed_user(db)
    project = _seed_project(db, user)
    req = Requirement(project_id=project.id, title="需求A", status="approved", source="manual")
    db.add(req)
    db.flush()
    older = datetime.utcnow() - timedelta(days=1)
    newer = datetime.utcnow()
    db.add_all(
        [
            TestCase(
                project_id=project.id,
                title="手动用例",
                review_status="approved",
                source="manual",
                created_at=older,
            ),
            TestCase(
                project_id=project.id,
                title="AI待评审",
                review_status="pending",
                source="ai_generated",
                requirement_id=req.id,
                created_at=newer,
            ),
            TestCase(
                project_id=project.id,
                title="AI已通过",
                review_status="approved",
                source="ai_generated",
                created_at=older,
            ),
        ]
    )
    db.add(
        ManualTestRun(
            project_id=project.id,
            name="已完成单",
            status="finished",
            pass_rate=88.5,
            finished_at=newer,
        )
    )
    db.add(ManualTestRun(project_id=project.id, name="执行中", status="running"))
    db.commit()

    out = get_functional_overview(db, project.id)
    assert out["case_total"] == 3
    assert out["pending_review_count"] == 1
    assert out["ai_generated_count"] == 2
    assert out["ai_pending_review_count"] == 1
    assert out["running_run_count"] == 1
    assert out["last_completed_pass_rate"] == 88.5

    api_out = functional_overview(project.id, db, user)
    assert api_out["case_total"] == 3


def test_list_testcases_source_and_created_at_order(db):
    user = _seed_user(db, "tc_filter")
    project = _seed_project(db, user)
    older = datetime.utcnow() - timedelta(days=2)
    newer = datetime.utcnow()
    db.add_all(
        [
            TestCase(
                project_id=project.id,
                title="旧AI",
                source="ai_generated",
                review_status="pending",
                created_at=older,
            ),
            TestCase(
                project_id=project.id,
                title="新AI",
                source="ai_generated",
                review_status="pending",
                created_at=newer,
            ),
            TestCase(
                project_id=project.id,
                title="手动",
                source="manual",
                review_status="draft",
                created_at=newer,
            ),
        ]
    )
    db.commit()

    page = list_testcases(
        project_id=project.id,
        requirement_id=None,
        review_status=None,
        source="ai_generated",
        order="created_at_desc",
        keyword=None,
        page=1,
        page_size=10,
        db=db,
        current_user=user,
    )
    assert page.total == 2
    assert [item.title for item in page.items] == ["新AI", "旧AI"]

    with pytest.raises(HTTPException) as exc:
        list_testcases(
            project_id=project.id,
            requirement_id=None,
            review_status=None,
            source="invalid",
            order=None,
            keyword=None,
            page=1,
            page_size=10,
            db=db,
            current_user=user,
        )
    assert exc.value.status_code == 400

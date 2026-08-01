import pytest
from fastapi import HTTPException

from app.models.user import User
from app.routers.projects import create_project, update_project
from app.schemas import ProjectCreate, ProjectUpdate


def _seed_user(db, username: str = "owner") -> User:
    user = User(username=username, hashed_password="hashed", role="tester")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_create_project_rejects_duplicate_name(db):
    user = _seed_user(db)
    create_project(ProjectCreate(name="AI质量平台"), db, user)

    with pytest.raises(HTTPException) as exc_info:
        create_project(ProjectCreate(name="AI质量平台"), db, user)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "项目名称已存在"


def test_create_project_trims_name_before_uniqueness_check(db):
    user = _seed_user(db)
    create_project(ProjectCreate(name=" 测试项目 "), db, user)

    with pytest.raises(HTTPException) as exc_info:
        create_project(ProjectCreate(name="测试项目"), db, user)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "项目名称已存在"


def test_update_project_rejects_duplicate_name(db):
    user = _seed_user(db)
    first = create_project(ProjectCreate(name="项目A"), db, user)
    second = create_project(ProjectCreate(name="项目B"), db, user)

    with pytest.raises(HTTPException) as exc_info:
        update_project(second.id, ProjectUpdate(name="项目A"), db, user)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "项目名称已存在"

    unchanged = update_project(first.id, ProjectUpdate(name="项目A"), db, user)
    assert unchanged.name == "项目A"

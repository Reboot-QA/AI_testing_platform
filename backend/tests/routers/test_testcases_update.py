import pytest
from fastapi import HTTPException

from app.models.project import Project
from app.models.requirement import Requirement
from app.models.testcase import TestCase as CaseModel
from app.models.user import User
from app.routers.testcases import update_testcase
from app.schemas import TestCaseUpdate as CaseUpdateSchema


def _seed_case(db):
    user = User(username="admin", hashed_password="hashed", role="admin")
    db.add(user)
    db.flush()

    project = Project(name="项目一", owner_id=user.id)
    other_project = Project(name="项目二", owner_id=user.id)
    db.add_all([project, other_project])
    db.flush()

    requirement = Requirement(project_id=project.id, title="本项目需求")
    other_requirement = Requirement(project_id=other_project.id, title="其他项目需求")
    case = CaseModel(project_id=project.id, title="待编辑用例")
    db.add_all([requirement, other_requirement, case])
    db.commit()
    return user, case, requirement, other_requirement


def test_update_testcase_accepts_same_project_requirement_and_review_status(db):
    user, case, requirement, _ = _seed_case(db)

    result = update_testcase(
        case.id,
        CaseUpdateSchema(requirement_id=requirement.id, review_status="approved"),
        db,
        user,
    )

    assert result.requirement_id == requirement.id
    assert result.review_status == "approved"


def test_update_testcase_rejects_cross_project_requirement(db):
    user, case, _, other_requirement = _seed_case(db)

    with pytest.raises(HTTPException) as exc_info:
        update_testcase(
            case.id,
            CaseUpdateSchema(requirement_id=other_requirement.id),
            db,
            user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "关联需求不存在或不属于当前项目"


def test_update_testcase_rejects_invalid_review_status(db):
    user, case, _, _ = _seed_case(db)

    with pytest.raises(HTTPException) as exc_info:
        update_testcase(
            case.id,
            CaseUpdateSchema(review_status="invalid"),
            db,
            user,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "无效的评审状态"

from app.models.project import Project
from app.models.user import User
from app.services.apifox import workbench_service


def test_overview_project_card_contains_description(db):
    user = User(username="admin", hashed_password="hashed", role="admin")
    db.add(user)
    db.flush()
    project = Project(name="质量平台", description="项目描述", owner_id=user.id)
    db.add(project)
    db.commit()

    overview = workbench_service.get_overview(db, user)

    assert overview["projects"][0]["description"] == "项目描述"

"""功能用例 Hub 任务单项目并发上限 → 排队 pending。"""


from app.models.hub_ai_task import HubAiTask
from app.models.project import Project
from app.models.user import User
from app.services import hub_ai_task_service as svc


def test_functional_hub_task_capacity_queues_as_pending(db):
    user = User(username="fn-cap", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    project = Project(name="fn-cap-p", owner_id=user.id)
    db.add(project)
    db.commit()

    db.add(
        HubAiTask(
            project_id=project.id,
            task_type="functional",
            created_by=user.id,
            status="running",
            target="t1",
        )
    )
    db.commit()

    msg = svc.hub_running_task_capacity_message(
        db, project.id, creating_task_type="functional"
    )
    assert msg is not None
    assert "用例生成" in msg

    task = svc.create_running_task(
        db,
        project_id=project.id,
        task_type="functional",
        created_by=user.id,
        target="t2",
    )
    assert task.status == "pending"

"""Hub AI 任务并发与补入库批次限制。"""

from app.models.hub_ai_task import HubAiTask
from app.models.project import Project
from app.models.user import User
from app.services import hub_ai_task_service as svc


def test_hub_running_task_capacity(db):
    user = User(username="cap", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    project = Project(name="cap-p", owner_id=user.id)
    db.add(project)
    db.commit()
    for i in range(svc.MAX_CONCURRENT_RUNNING_HUB_TASKS):
        db.add(
            HubAiTask(
                project_id=project.id,
                task_type="requirement",
                created_by=user.id,
                status="running",
                target=f"t{i}",
            )
        )
    db.commit()
    msg = svc.hub_running_task_capacity_message(db, project.id)
    assert msg is not None
    assert str(svc.MAX_CONCURRENT_RUNNING_HUB_TASKS) in msg

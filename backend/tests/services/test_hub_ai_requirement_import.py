"""Hub AI 需求任务：明细行随生成逐条入库（补同步）。"""

from app.models.hub_ai_task import HubAiTask
from app.models.hub_ai_task_requirement_item import HubAiTaskRequirementItem
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.user import User
from app.services import hub_ai_task_service as svc


def test_sync_unimported_requirement_items_persists_drafts(db):
    user = User(username="hub_req", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    project = Project(name="Hub 需求任务", owner_id=user.id)
    db.add(project)
    db.commit()

    task = HubAiTask(
        project_id=project.id,
        task_type="requirement",
        created_by=user.id,
        status="running",
        target="doc.txt",
        generated_total=1,
        applied_total=0,
    )
    db.add(task)
    db.flush()
    row = HubAiTaskRequirementItem(
        task_id=task.id,
        sort_order=1,
        title="登录功能",
        description="用户登录",
        req_type="functional",
        priority="P1",
    )
    db.add(row)
    db.commit()

    synced = svc.sync_unimported_requirement_items(db, task.id)
    assert synced == 1

    db.refresh(row)
    db.refresh(task)
    assert row.imported_at is not None
    assert row.requirement_id is not None
    assert task.applied_total == 1

    req = db.query(Requirement).filter(Requirement.id == row.requirement_id).one()
    assert req.title == "登录功能"
    assert req.project_id == project.id
    assert req.source == "ai_document"

    items = svc.list_requirement_items(db, task.id)
    assert len(items) == 1
    assert items[0]["imported_at"] is not None
    assert items[0]["requirement_id"] == row.requirement_id

    assert svc.sync_unimported_requirement_items(db, task.id) == 0

"""需求解析 Hub 任务单项目并发上限 → 排队 pending。"""


from app.models.hub_ai_task import HubAiTask
from app.models.project import Project
from app.models.user import User
from app.services import hub_ai_task_service as svc


def test_requirement_hub_task_capacity_queues_as_pending(db):
    user = User(username="req-cap", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    project = Project(name="req-cap-p", owner_id=user.id)
    db.add(project)
    db.commit()

    db.add(
        HubAiTask(
            project_id=project.id,
            task_type="requirement",
            created_by=user.id,
            status="running",
            target="t1",
        )
    )
    db.commit()

    msg = svc.hub_running_task_capacity_message(
        db, project.id, creating_task_type="requirement"
    )
    assert msg is not None
    assert "需求解析" in msg

    task = svc.create_running_task(
        db,
        project_id=project.id,
        task_type="requirement",
        created_by=user.id,
        target="t2",
    )
    assert task.status == "pending"


def test_requirement_global_queue_promote(db):
    user = User(username="req-g", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    p1 = Project(name="req-g-1", owner_id=user.id)
    p2 = Project(name="req-g-2", owner_id=user.id)
    db.add_all([p1, p2])
    db.commit()

    running = svc.create_running_task(
        db,
        project_id=p1.id,
        task_type="requirement",
        created_by=user.id,
        target="a",
    )
    assert running.status == "running"

    queued = svc.create_running_task(
        db,
        project_id=p2.id,
        task_type="requirement",
        created_by=user.id,
        target="b",
    )
    assert queued.status == "pending"
    svc.set_task_sse_waiting(db, queued.id, True)

    svc.finish_task(db, running.id, status="succeeded", generated_total=1)
    db.refresh(queued)
    assert queued.status == "running"


def test_requirement_finish_does_not_promote_without_sse_wait(db):
    user = User(username="req-nw", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    p1 = Project(name="req-nw-1", owner_id=user.id)
    p2 = Project(name="req-nw-2", owner_id=user.id)
    db.add_all([p1, p2])
    db.commit()

    running = svc.create_running_task(
        db,
        project_id=p1.id,
        task_type="requirement",
        created_by=user.id,
        target="a",
        provider_id=9,
    )
    queued = svc.create_running_task(
        db,
        project_id=p2.id,
        task_type="requirement",
        created_by=user.id,
        target="b",
        provider_id=9,
    )
    assert queued.status == "pending"

    svc.finish_task(db, running.id, status="succeeded", generated_total=1)
    db.refresh(queued)
    assert queued.status == "pending"


def test_llm_slot_key_differs_by_model_without_provider_id():
    a = svc.llm_slot_key_from_config(
        {"provider_id": None, "api_base": "https://a", "model": "m1", "provider_name": "A"}
    )
    b = svc.llm_slot_key_from_config(
        {"provider_id": None, "api_base": "https://b", "model": "m2", "provider_name": "B"}
    )
    assert a != b


def test_requirement_different_providers_run_without_queue(db):
    user = User(username="req-m", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    p1 = Project(name="req-m-1", owner_id=user.id)
    p2 = Project(name="req-m-2", owner_id=user.id)
    db.add_all([p1, p2])
    db.commit()

    a = svc.create_running_task(
        db,
        project_id=p1.id,
        task_type="requirement",
        created_by=user.id,
        target="a",
        provider_id=101,
    )
    b = svc.create_running_task(
        db,
        project_id=p2.id,
        task_type="requirement",
        created_by=user.id,
        target="b",
        provider_id=202,
    )
    assert a.status == "running"
    assert b.status == "running"


def test_requirement_same_provider_second_queues(db):
    user = User(username="req-s", hashed_password="x", role="tester")
    db.add(user)
    db.commit()
    p1 = Project(name="req-s-1", owner_id=user.id)
    p2 = Project(name="req-s-2", owner_id=user.id)
    db.add_all([p1, p2])
    db.commit()

    first = svc.create_running_task(
        db,
        project_id=p1.id,
        task_type="requirement",
        created_by=user.id,
        target="a",
        provider_id=9,
    )
    second = svc.create_running_task(
        db,
        project_id=p2.id,
        task_type="requirement",
        created_by=user.id,
        target="b",
        provider_id=9,
    )
    assert first.status == "running"
    assert second.status == "pending"

"""僵死 Hub AI 任务自动标记失败。"""

import json
from datetime import datetime, timedelta

from app.models.hub_ai_task import HUB_AI_TASK_ORPHAN_MINUTES, HUB_AI_TASK_STALE_MINUTES, HubAiTask
from app.services import hub_ai_task_service as svc


def test_fail_stale_running_tasks_uses_progress_at(db):
    user_id = 1
    task = HubAiTask(
        project_id=1,
        task_type="requirement",
        created_by=user_id,
        status="running",
        target="stale.txt",
        progress_at=datetime.utcnow() - timedelta(minutes=HUB_AI_TASK_STALE_MINUTES + 1),
        updated_at=datetime.utcnow(),
        meta_json=json.dumps(
            {
                "parse_worker_active": True,
                "parse_worker_at": datetime.utcnow().isoformat(),
            }
        ),
    )
    db.add(task)
    db.commit()
    n = svc.fail_stale_running_tasks(db)
    assert n == 1
    db.refresh(task)
    assert task.status == "failed"
    assert task.error


def test_fail_stale_orphan_running_without_worker(db):
    task = HubAiTask(
        project_id=1,
        task_type="requirement",
        created_by=1,
        status="running",
        target="orphan.txt",
        progress_at=datetime.utcnow(),
        updated_at=datetime.utcnow() - timedelta(minutes=HUB_AI_TASK_ORPHAN_MINUTES + 1),
    )
    db.add(task)
    db.commit()
    n = svc.fail_stale_running_tasks(db)
    assert n == 1
    db.refresh(task)
    assert task.status == "failed"


def test_requirement_parse_heartbeat_does_not_refresh_progress_at(db):
    old_progress = datetime.utcnow() - timedelta(minutes=HUB_AI_TASK_STALE_MINUTES + 1)
    task = HubAiTask(
        project_id=1,
        task_type="requirement",
        created_by=1,
        status="running",
        target="hb.txt",
        done_items=3,
        total_items=8,
        progress_at=old_progress,
        updated_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    svc.update_requirement_parse_heartbeat(
        db,
        task.id,
        segments_done=3,
        segment_total=8,
        segment_in_flight=4,
        generated_total=10,
        segments_in_flight_count=2,
    )
    db.refresh(task)
    assert task.progress_at == old_progress
    assert task.updated_at >= old_progress
    n = svc.fail_stale_running_tasks(db)
    assert n == 1
    db.refresh(task)
    assert task.status == "partial"

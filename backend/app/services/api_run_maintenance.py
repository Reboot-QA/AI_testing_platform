from typing import Iterable, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.api_automation import ApiScheduledTask, ApiTestRun
from app.services.schedule_service import get_task_last_run_ids, set_task_last_runs


def _sync_schedule_last_runs(db: Session, deleted_run_ids: Iterable[int]) -> None:
    deleted_set = set(deleted_run_ids)
    if not deleted_set:
        return

    db.query(ApiScheduledTask).filter(ApiScheduledTask.last_run_id.in_(deleted_set)).update(
        {ApiScheduledTask.last_run_id: None},
        synchronize_session=False,
    )

    for task in db.query(ApiScheduledTask).all():
        run_ids = get_task_last_run_ids(task)
        if not run_ids:
            continue
        remaining_ids = [run_id for run_id in run_ids if run_id not in deleted_set]
        if remaining_ids == run_ids:
            continue
        status = task.last_run_status or "failed"
        if not remaining_ids:
            status = "failed"
        set_task_last_runs(task, remaining_ids, status)


def after_api_test_runs_deleted(db: Session, deleted_run_ids: Iterable[int]) -> None:
    """Clear schedule refs and reset run ID sequence when no reports remain."""
    ids: List[int] = list(dict.fromkeys(deleted_run_ids))
    if ids:
        _sync_schedule_last_runs(db, ids)

    if db.query(ApiTestRun.id).limit(1).first() is not None:
        return

    dialect = db.bind.dialect.name
    if dialect == "mysql":
        db.execute(text("ALTER TABLE api_test_runs AUTO_INCREMENT = 1"))
        db.execute(text("ALTER TABLE api_test_step_results AUTO_INCREMENT = 1"))
    elif dialect == "sqlite":
        db.execute(
            text(
                "DELETE FROM sqlite_sequence "
                "WHERE name IN ('api_test_runs', 'api_test_step_results')"
            )
        )

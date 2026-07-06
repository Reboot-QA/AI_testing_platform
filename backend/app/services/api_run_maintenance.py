from typing import Iterable

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.api_automation import ApiScheduledTask, ApiTestRun


def after_api_test_runs_deleted(db: Session, deleted_run_ids: Iterable[int]) -> None:
    """Clear schedule refs and reset run ID sequence when no reports remain."""
    ids = list(dict.fromkeys(deleted_run_ids))
    if ids:
        db.query(ApiScheduledTask).filter(ApiScheduledTask.last_run_id.in_(ids)).update(
            {ApiScheduledTask.last_run_id: None},
            synchronize_session=False,
        )

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

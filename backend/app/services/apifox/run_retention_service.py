"""用例级测试报告保留策略：超过保留期的 case 运行记录自动物理删除（场景/套件报告不受影响）。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.apifox.run import ApifoxRun
from app.repositories.apifox import run_repo

logger = logging.getLogger(__name__)

CASE_RUN_RETENTION_DAYS = 30
_BATCH_SIZE = 200


def purge_expired_case_runs(db: Session) -> int:
    """删除 started_at 早于保留期的 target_type=case 运行（含重试链各次尝试、步骤）。"""
    cutoff = datetime.utcnow() - timedelta(days=CASE_RUN_RETENTION_DAYS)
    total = 0
    while True:
        ids = [
            row[0]
            for row in db.query(ApifoxRun.id)
            .filter(ApifoxRun.target_type == "case", ApifoxRun.started_at < cutoff)
            .order_by(ApifoxRun.id)
            .limit(_BATCH_SIZE)
            .all()
        ]
        if not ids:
            break
        total += run_repo.delete_runs(db, ids)
        db.commit()
    if total:
        logger.info(
            "用例运行报告过期清理：删除 %s 条（保留 %s 天内）",
            total,
            CASE_RUN_RETENTION_DAYS,
        )
    return total

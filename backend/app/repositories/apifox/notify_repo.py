"""Apifox 失败通知配置 · 数据访问（项目一对一，无则惰性创建）。"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.apifox.notify_config import ApifoxNotifyConfig


def get_by_project(db: Session, project_id: int) -> Optional[ApifoxNotifyConfig]:
    return (
        db.query(ApifoxNotifyConfig)
        .filter(ApifoxNotifyConfig.project_id == project_id)
        .first()
    )


def get_or_create(db: Session, project_id: int) -> ApifoxNotifyConfig:
    cfg = get_by_project(db, project_id)
    if cfg is None:
        cfg = ApifoxNotifyConfig(project_id=project_id)
        db.add(cfg)
        db.flush()
    return cfg

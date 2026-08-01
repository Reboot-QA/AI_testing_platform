"""Apifox 场景文件夹 · 业务层（复用 apifox_folders，kind='scenario'，单层分组）。

删除文件夹时其下场景**级联软删进回收站**（可还原），被引用的场景阻止删除。写操作末尾 commit。
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxFolder
from app.repositories.apifox import scenario_repo as repo
from app.routers.apifox.scenario_schemas import ScenarioFolderOut


def _out(db: Session, folder: ApifoxFolder) -> ScenarioFolderOut:
    return ScenarioFolderOut(
        id=folder.id, name=folder.name, scenario_count=repo.count_folder_scenarios(db, folder.id)
    )


def list_folders(db: Session, project_id: int) -> List[ScenarioFolderOut]:
    return [_out(db, f) for f in repo.list_scenario_folders(db, project_id)]


def create_folder(db: Session, project_id: int, name: str) -> ScenarioFolderOut:
    folder = ApifoxFolder(project_id=project_id, name=name, kind="scenario")
    repo.add(db, folder)
    db.commit()
    db.refresh(folder)
    return _out(db, folder)


def rename_folder(db: Session, folder: ApifoxFolder, name: str) -> ScenarioFolderOut:
    folder.name = name
    db.commit()
    db.refresh(folder)
    return _out(db, folder)


def delete_folder(db: Session, folder: ApifoxFolder, deleted_by: Optional[int] = None) -> None:
    """删除文件夹；其下场景级联软删进回收站（可还原）。被引用的子场景阻止删除，避免悬空引用。"""
    scenarios = repo.list_folder_scenarios(db, folder.id)
    for s in scenarios:
        refs = repo.count_scenario_refs(db, s.id)
        if refs:
            raise ValueError(f"场景「{s.name}」被 {refs} 处其他场景作为子场景引用，请先解除引用再删文件夹")
    now = datetime.utcnow()
    for s in scenarios:
        s.deleted_at = now
        s.deleted_by = deleted_by
        s.folder_id = None  # 解除 FK，便于删 apifox_folders 行；还原后落未分组（原文件夹已删）

    # 回收站里仍挂在该文件夹下的场景同样要解除 FK（否则 MySQL 报 1451 外键违反 → 500）；
    # 只动 folder_id，保留原本的删除时间与操作人
    for s in repo.list_deleted_scenarios(db, folder.project_id):
        if s.folder_id == folder.id:
            s.folder_id = None

    repo.delete(db, folder)
    db.commit()

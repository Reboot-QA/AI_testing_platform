"""Apifox 场景文件夹 · 业务层（复用 apifox_folders，kind='scenario'，单层分组）。

删除文件夹时其下场景移到未分组（folder_id=None），不级联删场景。写操作末尾 commit。
"""

from typing import List

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


def delete_folder(db: Session, folder: ApifoxFolder) -> None:
    repo.clear_folder_on_scenarios(db, folder.id)  # 其下场景移到未分组，不删场景
    repo.delete(db, folder)
    db.commit()

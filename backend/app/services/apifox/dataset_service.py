"""Apifox 项目级数据集 · 业务层（CRUD + bulk 行替换 + 引用计数/删除保护）。

引用计数 = 项目内多少用例的数据驱动 source=dataset 指向本数据集（删除前置校验）。
非法输入抛 ValueError（router 转 400）。写操作末尾 commit。权限在 router。
"""

import json
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.apifox.dataset import ApifoxDataset, ApifoxDatasetRow
from app.repositories.apifox import case_repo, scenario_repo
from app.repositories.apifox import dataset_repo as repo
from app.routers.apifox.dataset_schemas import (
    DatasetBrief,
    DatasetCreate,
    DatasetOut,
    DatasetRowIn,
    DatasetUpdate,
)


def _loads(text, fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return fallback


def _require_unique_name(db: Session, project_id: int, name: str, exclude_id: int | None = None) -> None:
    for s in repo.list_datasets(db, project_id):
        if s.name == name and s.id != exclude_id:
            raise ValueError("数据集名已存在")


def _dataset_ref_counts(db: Session, project_id: int) -> Dict[int, int]:
    """项目内各数据集被引用次数：用例数据驱动(source=dataset) + 场景运行配置(run_config.dataset_id)。"""
    counts: Dict[int, int] = {}
    for case in case_repo.list_cases_by_project(db, project_id):
        drive = _loads(case.data_drive, {})
        if drive.get("source") == "dataset" and drive.get("dataset_id"):
            did = int(drive["dataset_id"])
            counts[did] = counts.get(did, 0) + 1
    for scenario in scenario_repo.list_scenarios(db, project_id):
        cfg = _loads(scenario.run_config, {})
        if cfg.get("dataset_id"):
            did = int(cfg["dataset_id"])
            counts[did] = counts.get(did, 0) + 1
    return counts


def _write_rows(db: Session, dataset: ApifoxDataset, rows: List[DatasetRowIn]) -> None:
    for i, row in enumerate(rows):
        repo.add(
            db,
            ApifoxDatasetRow(
                dataset_id=dataset.id,
                values=json.dumps(row.values, ensure_ascii=False),
                enabled=row.enabled,
                sort_order=i,
            ),
        )


def _out(db: Session, dataset: ApifoxDataset) -> DatasetOut:
    return DatasetOut(
        id=dataset.id,
        project_id=dataset.project_id,
        name=dataset.name,
        description=dataset.description,
        columns=_loads(dataset.columns, []),
        rows=[
            DatasetRowIn(values=_loads(r.values, {}), enabled=r.enabled)
            for r in repo.list_rows(db, dataset.id)
        ],
        sort_order=dataset.sort_order,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


def list_datasets(db: Session, project_id: int) -> List[DatasetBrief]:
    ref_counts = _dataset_ref_counts(db, project_id)
    return [
        DatasetBrief(
            id=s.id,
            name=s.name,
            description=s.description,
            column_count=len(_loads(s.columns, [])),
            row_count=repo.count_rows(db, s.id),
            sort_order=s.sort_order,
            ref_count=ref_counts.get(s.id, 0),
        )
        for s in repo.list_datasets(db, project_id)
    ]


def create_dataset(db: Session, project_id: int, data: DatasetCreate) -> DatasetOut:
    _require_unique_name(db, project_id, data.name)
    dataset = ApifoxDataset(
        project_id=project_id,
        name=data.name,
        description=data.description,
        columns=json.dumps(data.columns, ensure_ascii=False),
    )
    repo.add(db, dataset)
    _write_rows(db, dataset, data.rows)
    db.commit()
    db.refresh(dataset)
    return _out(db, dataset)


def get_dataset_out(db: Session, dataset: ApifoxDataset) -> DatasetOut:
    return _out(db, dataset)


def update_dataset(db: Session, dataset: ApifoxDataset, data: DatasetUpdate) -> DatasetOut:
    if data.name is not None and data.name != dataset.name:
        _require_unique_name(db, dataset.project_id, data.name, exclude_id=dataset.id)
        dataset.name = data.name
    if "description" in data.model_fields_set:
        dataset.description = data.description
    if data.columns is not None:
        dataset.columns = json.dumps(data.columns, ensure_ascii=False)
    if data.sort_order is not None:
        dataset.sort_order = data.sort_order
    if data.rows is not None:
        repo.delete_rows(db, dataset.id)
        _write_rows(db, dataset, data.rows)
    db.commit()
    db.refresh(dataset)
    return _out(db, dataset)


def delete_dataset(db: Session, dataset: ApifoxDataset) -> None:
    refs = _dataset_ref_counts(db, dataset.project_id).get(dataset.id, 0)
    if refs:
        raise ValueError(f"数据集被 {refs} 处引用（用例数据驱动 / 场景运行配置），请先解除引用再删除")
    repo.delete_rows(db, dataset.id)
    repo.delete(db, dataset)
    db.commit()

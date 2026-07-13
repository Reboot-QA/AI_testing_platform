"""Apifox 项目级数据集 · 数据访问层（数据集 + 行）。不含业务校验；不提交事务。"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.dataset import ApifoxDataset, ApifoxDatasetRow


def list_datasets(db: Session, project_id: int) -> List[ApifoxDataset]:
    return (
        db.query(ApifoxDataset)
        .filter(ApifoxDataset.project_id == project_id)
        .order_by(ApifoxDataset.sort_order, ApifoxDataset.id)
        .all()
    )


def get_dataset(db: Session, dataset_id: int) -> Optional[ApifoxDataset]:
    return db.query(ApifoxDataset).filter(ApifoxDataset.id == dataset_id).first()


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


def delete(db: Session, obj) -> None:
    db.delete(obj)


def list_rows(db: Session, dataset_id: int) -> List[ApifoxDatasetRow]:
    return (
        db.query(ApifoxDatasetRow)
        .filter(ApifoxDatasetRow.dataset_id == dataset_id)
        .order_by(ApifoxDatasetRow.sort_order, ApifoxDatasetRow.id)
        .all()
    )


def count_rows(db: Session, dataset_id: int) -> int:
    return db.query(ApifoxDatasetRow).filter(ApifoxDatasetRow.dataset_id == dataset_id).count()


def delete_rows(db: Session, dataset_id: int) -> None:
    db.query(ApifoxDatasetRow).filter(ApifoxDatasetRow.dataset_id == dataset_id).delete(
        synchronize_session=False
    )

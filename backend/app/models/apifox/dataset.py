"""Apifox 重构 · 项目级静态数据集（可复用测试数据表，供用例数据驱动引用）。

数据集 = 命名的列 + 多行值；用例的数据驱动可选「数据源=数据集」按行迭代执行。
行用行级表落库（非整表 JSON blob），利于未来单行并发编辑；每行 values 存 {列名:值} JSON。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxDataset(Base):
    __tablename__ = "apifox_datasets"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_apifox_dataset_project_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 列名有序列表 JSON（表头；空行也能保留列结构）
    columns: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # 乐观锁版本：每次保存 +1，多人并发编辑冲突检测
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ApifoxDatasetRow(Base):
    __tablename__ = "apifox_dataset_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("apifox_datasets.id"), index=True)
    # {列名: 值} JSON
    values: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

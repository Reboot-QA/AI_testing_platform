"""Apifox 脚本调试预设 · 模型（项目级共享，成员皆可用）。

保存脚本调试弹窗里的一组输入（阶段 + 变量 + 响应上下文），跟着项目走、跨设备/成员共享。
按 (project_id, name) 唯一，同名即覆盖（与前端"同名覆盖"一致）。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxScriptDebugPreset(Base):
    __tablename__ = "apifox_script_debug_presets"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_apifox_debug_preset_proj_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(200))
    phase: Mapped[str] = mapped_column(String(10), default="pre")  # pre | post
    variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 变量字典
    response_status: Mapped[int] = mapped_column(Integer, default=200)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 记录创建者，仅信息用

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

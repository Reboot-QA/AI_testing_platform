"""项目成员（显式授权，跨部门把指定用户加进某项目）。

区别于"同部门自动可见"：成员是一条真实授权记录，让被加入者仅获得该项目权限，不影响
其部门可见性。一个用户可加入多个项目。成员在项目内权限等同管理员，但不能删项目/改项目名。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 操作人，仅信息用
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

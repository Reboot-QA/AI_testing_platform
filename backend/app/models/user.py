from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="tester")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)
    # Workbench 重构：一人一组织（软引用 organizations.id，避开循环外键）
    organization_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    # Workbench 重构：会员归属团队（软引用 teams.id，仅作归属标签，不参与权限判定）
    team_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects: Mapped[List["Project"]] = relationship("Project", back_populates="owner")
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="users")


from app.models.project import Project  # noqa: E402
from app.models.department import Department  # noqa: E402

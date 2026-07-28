from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner_seq: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    api_global_variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 上次 OpenAPI 导入的 URL（同源再次导入时智能识别为「更新同步」并预览；也用于回填）
    last_import_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="projects")
    requirements: Mapped[List["Requirement"]] = relationship(
        "Requirement", back_populates="project", cascade="all, delete-orphan"
    )
    testcases: Mapped[List["TestCase"]] = relationship(
        "TestCase", back_populates="project", cascade="all, delete-orphan"
    )
    manual_test_runs: Mapped[List["ManualTestRun"]] = relationship(
        "ManualTestRun", back_populates="project", cascade="all, delete-orphan"
    )


from app.models.department import Department  # noqa: E402
from app.models.requirement import Requirement  # noqa: E402
from app.models.test_execution import ManualTestRun  # noqa: E402
from app.models.testcase import TestCase  # noqa: E402
from app.models.user import User  # noqa: E402

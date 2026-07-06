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
    status: Mapped[str] = mapped_column(String(20), default="active")
    api_global_variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    requirements: Mapped[List["Requirement"]] = relationship(
        "Requirement", back_populates="project", cascade="all, delete-orphan"
    )
    testcases: Mapped[List["TestCase"]] = relationship(
        "TestCase", back_populates="project", cascade="all, delete-orphan"
    )
    api_environments: Mapped[List["ApiEnvironment"]] = relationship(
        "ApiEnvironment", back_populates="project", cascade="all, delete-orphan"
    )
    api_test_suites: Mapped[List["ApiTestSuite"]] = relationship(
        "ApiTestSuite", back_populates="project", cascade="all, delete-orphan"
    )
    manual_test_runs: Mapped[List["ManualTestRun"]] = relationship(
        "ManualTestRun", back_populates="project", cascade="all, delete-orphan"
    )


from app.models.user import User  # noqa: E402
from app.models.requirement import Requirement  # noqa: E402
from app.models.testcase import TestCase  # noqa: E402
from app.models.api_automation import ApiEnvironment, ApiTestSuite  # noqa: E402
from app.models.test_execution import ManualTestRun  # noqa: E402

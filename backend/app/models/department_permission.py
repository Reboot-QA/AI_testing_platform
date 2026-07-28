from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DepartmentMenuPermission(Base):
    __tablename__ = "department_menu_permissions"
    __table_args__ = (UniqueConstraint("department_id", "menu_key", name="uq_department_menu"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("departments.id", ondelete="CASCADE"), index=True
    )
    menu_key: Mapped[str] = mapped_column(String(50), index=True)

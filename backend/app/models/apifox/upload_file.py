"""Apifox 重构 · 上传文件（Binary body 用）。

文件字节直接存 DB（MEDIUMBLOB，容器/多实例零卷配置、随项目删除级联、随 DB 备份）。
仅存小型测试样例文件，service 层限大小（10MB）。锚定项目。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxUploadFile(Base):
    __tablename__ = "apifox_upload_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    filename: Mapped[str] = mapped_column(String(500), default="")
    content_type: Mapped[str] = mapped_column(String(200), default="application/octet-stream")
    size: Mapped[int] = mapped_column(Integer, default=0)
    # MEDIUMBLOB（16MB 容量上限）承载文件字节；service 限 10MB
    data: Mapped[bytes] = mapped_column(LargeBinary(16 * 1024 * 1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

"""Apifox 上传文件 · 响应契约（仅元数据，不含字节）。"""

from datetime import datetime

from pydantic import BaseModel


class UploadOut(BaseModel):
    id: int
    filename: str
    content_type: str
    size: int
    created_at: datetime

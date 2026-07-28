"""Apifox 项目级 API Token · 请求/响应契约。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ApiTokenCreate(BaseModel):
    name: str = "API Token"


class ApiTokenOut(BaseModel):
    id: int
    project_id: int
    name: str
    token: str
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

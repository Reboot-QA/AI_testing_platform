"""Apifox 环境数据库连接 · 请求/响应契约。密码只写不回显（Out 仅给 has_password）。"""

from typing import Optional

from pydantic import BaseModel, Field


class DatabaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    db_type: str = "mysql"
    host: str = ""
    port: int = 3306
    username: str = ""
    password: Optional[str] = None
    database: str = ""


class DatabaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    db_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    # 仅当非 None 时更新密码；None 表示保持原值不变
    password: Optional[str] = None
    database: Optional[str] = None
    sort_order: Optional[int] = None


class DatabaseOut(BaseModel):
    id: int
    environment_id: int
    name: str
    db_type: str
    host: str
    port: int
    username: str
    database: str
    has_password: bool = False
    sort_order: int

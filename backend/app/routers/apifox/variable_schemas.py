"""Apifox 环境·变量 · 请求/响应契约。

VariableOut 的 effective_value = 当前用户 local_value 若存在 else remote_value。
本切密文不脱敏（is_secret 仅标记），脱敏留后续。
"""

from typing import Optional

from pydantic import BaseModel, Field


# ---------- environment ----------
class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    base_url: Optional[str] = None
    is_default: bool = False


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    base_url: Optional[str] = None
    is_default: Optional[bool] = None
    sort_order: Optional[int] = None


class EnvironmentOut(BaseModel):
    id: int
    project_id: int
    name: str
    base_url: Optional[str] = None
    is_default: bool
    sort_order: int


# ---------- variable (环境变量 / 全局变量 共用) ----------
class VariableCreate(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    remote_value: Optional[str] = None
    is_secret: bool = False
    enabled: bool = True


class VariableUpdate(BaseModel):
    key: Optional[str] = Field(default=None, min_length=1, max_length=200)
    remote_value: Optional[str] = None
    is_secret: Optional[bool] = None
    enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class VariableOut(BaseModel):
    id: int
    key: str
    remote_value: Optional[str] = None
    local_value: Optional[str] = None  # 当前用户
    effective_value: Optional[str] = None  # local ?? remote
    is_secret: bool
    enabled: bool
    sort_order: int


class LocalValueSet(BaseModel):
    # 设当前用户本地值；local_value=null 表示清除本地覆盖（回退到远程值）
    local_value: Optional[str] = None

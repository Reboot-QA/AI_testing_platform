"""数据模型名称限长 50（Confluence 7/23-#10）。"""
import pytest
from pydantic import ValidationError

from app.constants.limits import MODEL_NAME_MAX_LEN
from app.routers.apifox.data_model_schemas import SchemaCreate


def test_model_name_limit_is_50():
    assert MODEL_NAME_MAX_LEN == 50


def test_model_name_over_limit_rejected():
    SchemaCreate(name="x" * 50)  # 恰好 50 通过
    with pytest.raises(ValidationError):
        SchemaCreate(name="x" * 51)

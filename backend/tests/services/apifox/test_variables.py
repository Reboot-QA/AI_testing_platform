"""variables 纯函数单元 · 插值 apply_vars / 合并 merge_vars / 行转字典 / 数据驱动行。"""

from types import SimpleNamespace

import pytest

from app.services.apifox.variables import (
    _rows_to_dict,
    apply_vars,
    case_variable_rows,
    data_drive_rows,
    merge_vars,
)


def _case(*, variables: str = "", data_drive: str = ""):
    """构造只暴露 variables/data_drive 两个 JSON 文本字段的用例替身。"""
    return SimpleNamespace(variables=variables, data_drive=data_drive)


# ---------- apply_vars ----------
def test_apply_vars_substitutes_known_variable():
    result = apply_vars("hi {{name}}", {"name": "bob"})

    assert result == "hi bob"


def test_apply_vars_keeps_placeholder_when_variable_missing():
    result = apply_vars("hi {{name}}", {})

    assert result == "hi {{name}}"


def test_apply_vars_substitutes_multiple_and_strips_key_whitespace():
    result = apply_vars("{{ a }}-{{b}}", {"a": "1", "b": "2"})

    assert result == "1-2"


@pytest.mark.parametrize("text", ["", None])
def test_apply_vars_empty_or_none_yields_empty_string(text):
    result = apply_vars(text, {"a": "1"})

    assert result == ""


# ---------- merge_vars ----------
def test_merge_vars_later_layer_overrides_earlier():
    merged = merge_vars({"a": "1", "b": "1"}, {"b": "2"})

    assert merged == {"a": "1", "b": "2"}


def test_merge_vars_skips_none_layers():
    merged = merge_vars({"a": "1"}, None, {"b": "2"})

    assert merged == {"a": "1", "b": "2"}


# ---------- _rows_to_dict ----------
def test_rows_to_dict_interpolates_value():
    rows = [{"key": "Authorization", "value": "Bearer {{token}}"}]

    result = _rows_to_dict(rows, {"token": "abc"})

    assert result == {"Authorization": "Bearer abc"}


def test_rows_to_dict_skips_disabled_and_empty_key_rows():
    rows = [
        {"key": "keep", "value": "y"},
        {"key": "drop", "value": "n", "enabled": False},
        {"key": "  ", "value": "z"},
    ]

    result = _rows_to_dict(rows, {})

    assert result == {"keep": "y"}


# ---------- case_variable_rows ----------
def test_case_variable_rows_keeps_enabled_only():
    case = _case(variables='[{"key": "a", "value": "1"}, {"key": "b", "value": "2", "enabled": false}]')

    result = case_variable_rows(case)

    assert result == {"a": "1"}


# ---------- data_drive_rows ----------
def test_data_drive_rows_returns_single_none_when_disabled():
    result = data_drive_rows(_case(data_drive=""))

    assert result == [None]


def test_data_drive_rows_expands_enabled_rows():
    drive = '{"enabled": true, "rows": [{"values": {"id": "1"}}, {"values": {"id": "2"}}]}'

    result = data_drive_rows(_case(data_drive=drive))

    assert result == [{"id": "1"}, {"id": "2"}]


def test_data_drive_rows_skips_disabled_row():
    drive = '{"enabled": true, "rows": [{"values": {"id": "1"}, "enabled": false}, {"values": {"id": "2"}}]}'

    result = data_drive_rows(_case(data_drive=drive))

    assert result == [{"id": "2"}]


def test_data_drive_rows_enabled_but_no_rows_falls_back_to_none():
    result = data_drive_rows(_case(data_drive='{"enabled": true, "rows": []}'))

    assert result == [None]

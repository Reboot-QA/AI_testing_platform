import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.api_variable_service import (
    apply_scoped_extractions,
    load_variables_json,
    merge_variable_context,
    normalize_scope,
)


def test_normalize_scope():
    assert normalize_scope("environment") == "environment"
    assert normalize_scope(None) == "temporary"
    assert normalize_scope("invalid") == "temporary"


def test_merge_variable_context_priority():
    merged = merge_variable_context(
        {"a": "global"},
        {"a": "env", "b": "env"},
        {"b": "runtime", "c": "runtime"},
        {"c": "case"},
    )
    assert merged == {"a": "env", "b": "runtime", "c": "case"}


def test_apply_scoped_extractions():
    runtime = {}
    env = {}
    global_vars = {}
    extracted = apply_scoped_extractions(
        [
            {"key": "temp", "value": "1", "scope": "temporary"},
            {"key": "token", "value": "abc", "scope": "environment"},
            {"key": "cfg", "value": "x", "scope": "global"},
        ],
        runtime,
        env,
        global_vars,
    )
    assert extracted == {"temp": "1", "token": "abc", "cfg": "x"}
    assert runtime == {"temp": "1", "token": "abc", "cfg": "x"}
    assert env == {"token": "abc"}
    assert global_vars == {"cfg": "x"}


def test_load_variables_json():
    assert load_variables_json('{"access_token":"t1"}') == {"access_token": "t1"}
    assert load_variables_json(None) == {}


if __name__ == "__main__":
    test_normalize_scope()
    test_merge_variable_context_priority()
    test_apply_scoped_extractions()
    test_load_variables_json()
    print("OK")

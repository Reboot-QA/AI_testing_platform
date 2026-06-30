import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.services.api_script_runner import run_pre_script


def test_python_pre_script_updates_variables():
    script = """
variables['timestamp'] = str(int(time.time()))
console.log('ready')
"""
    updated, logs, error = run_pre_script(script, "python", {"phone": "13800138000"})
    assert error is None, error
    assert "timestamp" in updated
    assert updated["phone"] == "13800138000"
    assert "ready" in logs[0]


def test_empty_script():
    updated, logs, error = run_pre_script("", "python", {"a": "1"})
    assert error is None
    assert updated == {"a": "1"}
    assert logs == []


def test_faker_pre_script():
    script = """
from faker import Faker
fake = Faker('zh_CN')
variables['phone'] = fake.phone_number()
print(variables['phone'])
"""
    updated, logs, error = run_pre_script(script, "python", {})
    assert error is None, error
    assert updated.get("phone")
    assert logs


if __name__ == "__main__":
    test_python_pre_script_updates_variables()
    test_empty_script()
    test_faker_pre_script()
    print("OK")

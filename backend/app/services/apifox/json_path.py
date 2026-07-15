import json
from typing import Any, Tuple


def resolve_json_path(data: Any, path: str) -> Tuple[bool, Any]:
    """Resolve JSON path. Returns (found, value); found=False when segment is missing."""
    if not path:
        return True, data

    normalized = path.strip()
    if normalized.startswith("$."):
        normalized = normalized[2:]
    elif normalized.startswith("$"):
        normalized = normalized[1:].lstrip(".")

    current = data
    parts = [part for part in normalized.replace("[", ".").replace("]", "").split(".") if part]

    for part in parts:
        if current is None:
            return False, None

        if isinstance(current, str):
            try:
                parsed = json.loads(current)
            except json.JSONDecodeError:
                return False, None
            if isinstance(parsed, (dict, list)):
                current = parsed
            else:
                return False, None

        if isinstance(current, dict):
            if part not in current:
                return False, None
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            if idx >= len(current):
                return False, None
            current = current[idx]
        else:
            return False, None

    return True, current


def extract_json_path(data: Any, path: str) -> Any:
    found, value = resolve_json_path(data, path)
    if not found:
        return None
    return value

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional

from app.services.log_service import MAX_LINE_LENGTH, MAX_RESPONSE_BYTES, MAX_TAIL_LINES, get_log_dir

ERROR_LOG_FILES = {
    "application": {"label": "应用错误", "filename": "errors.log"},
    "api": {"label": "接口错误", "filename": "api_errors.log"},
}

TIMESTAMP_PREFIX = re.compile(r"^\[(?P<ts>[^\]]+)\]")
UVICORN_ACCESS = re.compile(
    r'(?P<client>[\d\.]+(?::\d+)?)\s+-\s+"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+HTTP/[^"]+"\s+(?P<status>\d{3})'
)
APP_API_LINE = re.compile(
    r"(?P<client>\S+)\s+(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+->\s+HTTP\s+(?P<status>\d{3})\s+\|\s+(?P<detail>.*)$"
)
GENERIC_LOG = re.compile(
    r"\[(?P<ts>[^\]]+)\]\s+\[(?P<level>ERROR|ERR|CRITICAL|FATAL|WARNING|WARN)\]\s+\[(?P<logger>[^\]]+)\]\s+(?P<message>.*)$",
    re.IGNORECASE,
)
JSON_LINE = re.compile(r"^\s*\{")


def _truncate(text: str) -> str:
    if len(text) <= MAX_LINE_LENGTH:
        return text
    return text[: MAX_LINE_LENGTH - 3] + "..."


def _extract_timestamp(text: str) -> Optional[str]:
    match = TIMESTAMP_PREFIX.match(text)
    if not match:
        return None
    return match.group("ts").strip()


def _file_stats(path: Path) -> Dict:
    if not path.exists():
        return {"exists": False, "size": 0, "modified_at": None, "line_count": 0}
    stat = path.stat()
    line_count = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for _ in handle:
                line_count += 1
    except OSError:
        line_count = 0
    return {
        "exists": True,
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "line_count": line_count,
    }


def _resolve_error_file(category: str) -> Path:
    if category not in ERROR_LOG_FILES:
        raise ValueError(f"未知错误类别: {category}")
    return get_log_dir() / ERROR_LOG_FILES[category]["filename"]


def _parse_json_error_line(text: str, category: str) -> Optional[Dict]:
    if not JSON_LINE.match(text):
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    status = payload.get("status")
    if category == "api" and (not isinstance(status, int) or status < 400):
        return None
    return {
        "category": category,
        "level": "ERROR" if isinstance(status, int) and status >= 500 else "WARN",
        "timestamp": payload.get("timestamp") or payload.get("ts"),
        "client_ip": payload.get("client_ip") or payload.get("client"),
        "method": payload.get("method"),
        "path": payload.get("path"),
        "status": status,
        "logger": payload.get("logger") or f"app.{category}",
        "message": _truncate(str(payload.get("message") or payload.get("detail") or "")),
        "text": _truncate(text),
    }


def _parse_api_line(text: str, source: str, line_no: int) -> Optional[Dict]:
    json_entry = _parse_json_error_line(text, "api")
    if json_entry:
        json_entry["no"] = line_no
        json_entry["source"] = source
        return json_entry

    timestamp = _extract_timestamp(text)
    body = text
    if timestamp:
        body = text[text.index("]") + 1 :].strip()
        if body.startswith("["):
            body = body[body.index("]") + 1 :].strip()
        if body.startswith("["):
            body = body[body.index("]") + 1 :].strip()

    app_match = APP_API_LINE.search(body)
    if app_match:
        status = int(app_match.group("status"))
        if status < 400:
            return None
        return {
            "no": line_no,
            "source": source,
            "category": "api",
            "level": "ERROR" if status >= 500 else "WARN",
            "timestamp": timestamp,
            "client_ip": app_match.group("client"),
            "method": app_match.group("method"),
            "path": app_match.group("path"),
            "status": status,
            "logger": "app.api",
            "message": _truncate(app_match.group("detail").strip()),
            "text": _truncate(text),
        }

    access_match = UVICORN_ACCESS.search(body)
    if access_match:
        status = int(access_match.group("status"))
        if status < 400:
            return None
        return {
            "no": line_no,
            "source": source,
            "category": "api",
            "level": "ERROR" if status >= 500 else "WARN",
            "timestamp": timestamp,
            "client_ip": access_match.group("client").split(":")[0],
            "method": access_match.group("method"),
            "path": access_match.group("path"),
            "status": status,
            "logger": "uvicorn.access",
            "message": f"HTTP {status}",
            "text": _truncate(text),
        }
    return None


def _parse_application_line(text: str, source: str, line_no: int) -> Optional[Dict]:
    json_entry = _parse_json_error_line(text, "application")
    if json_entry:
        json_entry["no"] = line_no
        json_entry["source"] = source
        return json_entry

    match = GENERIC_LOG.match(text)
    if not match:
        return None

    logger_name = match.group("logger")
    level = match.group("level").upper()
    if level in {"ERR", "FATAL", "CRITICAL"}:
        level = "ERROR"
    elif level in {"WARN", "WARNING"}:
        level = "WARN"

    if logger_name == "uvicorn.access":
        return None
    if logger_name == "app.api":
        return None

    if level not in {"ERROR", "WARN"}:
        return None

    message = match.group("message").strip()
    if level == "WARN" and "Unhandled" not in message and "Traceback" not in message:
        return None

    return {
        "no": line_no,
        "source": source,
        "category": "application",
        "level": level,
        "timestamp": match.group("ts"),
        "client_ip": None,
        "method": None,
        "path": None,
        "status": None,
        "logger": logger_name,
        "message": _truncate(message),
        "text": _truncate(text),
    }


def _parse_line(text: str, category: str, source: str, line_no: int) -> Optional[Dict]:
    if category == "api":
        return _parse_api_line(text, source, line_no)
    if category == "application":
        return _parse_application_line(text, source, line_no)
    return _parse_api_line(text, source, line_no) or _parse_application_line(text, source, line_no)


def _iter_source_files(category: str) -> List[tuple[str, Path]]:
    log_dir = get_log_dir()
    files: List[tuple[str, Path]] = []
    if category in {"application", "all"}:
        files.append(("errors", _resolve_error_file("application")))
    if category in {"api", "all"}:
        files.append(("api_errors", _resolve_error_file("api")))
    files.append(("backend", log_dir / "backend.log"))
    if category in {"application", "all"}:
        files.append(("frontend", log_dir / "frontend.log"))
    return files


def _match_filters(
    entry: Dict,
    keyword_lower: Optional[str],
    status_min: Optional[int],
    method_upper: Optional[str],
) -> bool:
    if status_min is not None:
        status = entry.get("status")
        if status is None or status < status_min:
            return False
    if method_upper and (entry.get("method") or "").upper() != method_upper:
        return False
    if keyword_lower:
        haystack = " ".join(
            str(entry.get(key) or "")
            for key in ("text", "message", "path", "method", "logger", "client_ip")
        ).lower()
        if keyword_lower not in haystack:
            return False
    return True


def list_summary() -> Dict:
    log_dir = get_log_dir()
    categories = []
    for key, meta in ERROR_LOG_FILES.items():
        path = log_dir / meta["filename"]
        stats = _file_stats(path)
        categories.append(
            {
                "key": key,
                "label": meta["label"],
                "filename": meta["filename"],
                **stats,
            }
        )

    preview = tail_errors(category="all", lines=1)
    return {
        "log_dir": str(log_dir),
        "categories": categories,
        "recent_total": preview["total_matched"],
    }


def _dedupe_items(items: List[Dict]) -> List[Dict]:
    seen = set()
    deduped: List[Dict] = []
    for item in items:
        key = (
            item.get("timestamp"),
            item.get("method"),
            item.get("path"),
            item.get("status"),
            item.get("message"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def tail_errors(
    category: str = "all",
    lines: int = 200,
    keyword: Optional[str] = None,
    status_min: Optional[int] = None,
    method: Optional[str] = None,
    offset: int = 0,
) -> Dict:
    if category not in {"application", "api", "all"}:
        raise ValueError(f"未知错误类别: {category}")

    lines = max(1, min(lines, MAX_TAIL_LINES))
    offset = max(0, offset)
    keyword_lower = keyword.lower().strip() if keyword else None
    method_upper = method.upper().strip() if method else None
    if status_min is None and category == "api":
        status_min = 400

    matched: List[Dict] = []

    for source_key, path in _iter_source_files(category):
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_no, raw in enumerate(handle, start=1):
                text = raw.rstrip("\n\r")
                if not text:
                    continue
                entry = _parse_line(text, category, source_key, line_no)
                if not entry:
                    continue
                if not _match_filters(entry, keyword_lower, status_min, method_upper):
                    continue
                matched.append(entry)

    matched = _dedupe_items(matched)
    matched.sort(key=lambda item: (item.get("timestamp") or "", item.get("no") or 0))
    total = len(matched)
    page = matched[offset : offset + lines]

    return {
        "category": category,
        "items": page,
        "total_matched": total,
        "next_offset": offset + len(page),
    }


def stream_error_events(category: str = "all", poll_interval: float = 1.0) -> Generator[str, None, None]:
    if category not in {"application", "api", "all"}:
        raise ValueError(f"未知错误类别: {category}")

    tracked: Dict[str, int] = {}
    for _, path in _iter_source_files(category):
        tracked[str(path)] = path.stat().st_size if path.exists() else 0

    yield _sse_payload({"type": "connected", "category": category})

    while True:
        try:
            emitted = False
            for source_key, path in _iter_source_files(category):
                path_key = str(path)
                if not path.exists():
                    continue
                current_size = path.stat().st_size
                last_size = tracked.get(path_key, 0)
                if current_size < last_size:
                    tracked[path_key] = current_size
                    continue
                if current_size <= last_size:
                    continue
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(last_size)
                    chunk = handle.read(min(current_size - last_size, MAX_RESPONSE_BYTES))
                tracked[path_key] = current_size
                for raw in chunk.splitlines():
                    text = raw.rstrip("\r")
                    if not text:
                        continue
                    entry = _parse_line(text, category, source_key, None)
                    if not entry:
                        continue
                    if category == "api" and entry.get("status") is not None and entry["status"] < 400:
                        continue
                    entry["no"] = None
                    payload = {"type": "item", **entry}
                    yield _sse_payload(payload)
                    emitted = True
            if not emitted:
                yield _sse_payload({"type": "heartbeat"})
        except Exception as exc:
            yield _sse_payload({"type": "error", "message": str(exc)})
        time.sleep(poll_interval)


def _sse_payload(data: Dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

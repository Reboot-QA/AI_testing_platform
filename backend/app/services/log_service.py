import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

from app.config import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MAX_LINE_LENGTH = 4000
MAX_TAIL_LINES = 2000
MAX_RESPONSE_BYTES = 512 * 1024

LOG_SOURCES: Dict[str, Dict[str, str]] = {
    "backend": {"label": "后端服务", "filename": "backend.log"},
    "frontend": {"label": "前端服务", "filename": "frontend.log"},
    "ensure": {"label": "巡检恢复", "filename": "ensure.log"},
}

LEVEL_PATTERN = re.compile(r"\b(ERROR|ERR|CRITICAL|FATAL|WARN|WARNING|INFO|DEBUG|TRACE)\b", re.IGNORECASE)


def get_log_dir() -> Path:
    configured = (settings.log_dir or "").strip()
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = (PROJECT_ROOT / path).resolve()
        return path
    return (PROJECT_ROOT / ".deploy" / "logs").resolve()


def _resolve_source_path(source: str) -> Path:
    if source not in LOG_SOURCES:
        raise ValueError(f"未知日志来源: {source}")
    return get_log_dir() / LOG_SOURCES[source]["filename"]


def _detect_level(line: str) -> str:
    match = LEVEL_PATTERN.search(line)
    if not match:
        return "INFO"
    value = match.group(1).upper()
    if value in {"ERR", "FATAL", "CRITICAL"}:
        return "ERROR"
    if value in {"WARN", "WARNING"}:
        return "WARN"
    if value == "DEBUG":
        return "DEBUG"
    if value == "TRACE":
        return "DEBUG"
    return value


def _truncate_line(line: str) -> str:
    if len(line) <= MAX_LINE_LENGTH:
        return line
    return line[: MAX_LINE_LENGTH - 3] + "..."


def _file_stats(path: Path) -> Dict:
    if not path.exists():
        return {
            "exists": False,
            "size": 0,
            "modified_at": None,
            "line_count": 0,
        }
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


def list_sources() -> List[Dict]:
    log_dir = get_log_dir()
    items = []
    for key, meta in LOG_SOURCES.items():
        path = log_dir / meta["filename"]
        stats = _file_stats(path)
        items.append(
            {
                "key": key,
                "label": meta["label"],
                "filename": meta["filename"],
                "path": str(path),
                **stats,
            }
        )
    return items


def tail_log(
    source: str,
    lines: int = 200,
    keyword: Optional[str] = None,
    level: Optional[str] = None,
    offset: int = 0,
) -> Dict:
    path = _resolve_source_path(source)
    lines = max(1, min(lines, MAX_TAIL_LINES))
    offset = max(0, offset)

    if not path.exists():
        return {
            "source": source,
            "lines": [],
            "total_matched": 0,
            "next_offset": 0,
            "file_size": 0,
            "modified_at": None,
        }

    stats = _file_stats(path)
    collected: List[Dict] = []
    matched_total = 0
    keyword_lower = keyword.lower().strip() if keyword else None
    level_upper = level.upper().strip() if level else None

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, raw in enumerate(handle, start=1):
            text = raw.rstrip("\n\r")
            line_level = _detect_level(text)
            if level_upper and line_level != level_upper:
                continue
            if keyword_lower and keyword_lower not in text.lower():
                continue
            matched_total += 1
            if matched_total <= offset:
                continue
            collected.append(
                {
                    "no": index,
                    "level": line_level,
                    "text": _truncate_line(text),
                    "timestamp": None,
                }
            )
            if len(collected) >= lines:
                break

    return {
        "source": source,
        "lines": collected,
        "total_matched": matched_total,
        "next_offset": offset + len(collected),
        "file_size": stats["size"],
        "modified_at": stats["modified_at"],
    }


def read_log_chunk(source: str, start_line: int, limit: int = 200) -> Dict:
    path = _resolve_source_path(source)
    limit = max(1, min(limit, MAX_TAIL_LINES))
    start_line = max(1, start_line)
    items: List[Dict] = []

    if not path.exists():
        return {"source": source, "lines": [], "start_line": start_line, "has_more": False}

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, raw in enumerate(handle, start=1):
            if index < start_line:
                continue
            text = raw.rstrip("\n\r")
            items.append(
                {
                    "no": index,
                    "level": _detect_level(text),
                    "text": _truncate_line(text),
                    "timestamp": None,
                }
            )
            if len(items) >= limit:
                break

    has_more = len(items) == limit
    return {
        "source": source,
        "lines": items,
        "start_line": start_line,
        "has_more": has_more,
        "next_line": start_line + len(items) if items else start_line,
    }


def stream_log_events(source: str, poll_interval: float = 1.0) -> Generator[str, None, None]:
    path = _resolve_source_path(source)
    last_size = 0
    if path.exists():
        last_size = path.stat().st_size

    yield _sse_payload({"type": "connected", "source": source, "size": last_size})

    while True:
        try:
            if not path.exists():
                yield _sse_payload({"type": "heartbeat", "message": "日志文件不存在，等待创建..."})
                time.sleep(poll_interval)
                continue

            current_size = path.stat().st_size
            if current_size < last_size:
                last_size = 0
                yield _sse_payload({"type": "reset", "message": "日志文件已轮转或截断"})

            if current_size > last_size:
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(last_size)
                    chunk = handle.read(min(current_size - last_size, MAX_RESPONSE_BYTES))
                last_size = current_size
                for raw in chunk.splitlines():
                    text = raw.rstrip("\r")
                    if not text:
                        continue
                    yield _sse_payload(
                        {
                            "type": "line",
                            "no": None,
                            "level": _detect_level(text),
                            "text": _truncate_line(text),
                        }
                    )
            else:
                yield _sse_payload({"type": "heartbeat"})
        except Exception as exc:
            yield _sse_payload({"type": "error", "message": str(exc)})

        time.sleep(poll_interval)


def _sse_payload(data: Dict) -> str:
    import json

    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def get_download_path(source: str) -> Tuple[Path, str]:
    path = _resolve_source_path(source)
    filename = LOG_SOURCES[source]["filename"]
    return path, filename

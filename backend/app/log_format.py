"""日志格式化：异常堆栈每一行都带时间戳，便于 docker logs / 文件检索定位。"""

from __future__ import annotations

import logging


class MultilineTimestampFormatter(logging.Formatter):
    """标准 Formatter 只在首行加前缀，traceback 后续行无时间戳；本类为每行补齐。"""

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        prefix = f"[{self.formatTime(record)}] [{record.levelname}] [{record.name}] "
        lines = [prefix + record.message]

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            lines.extend(prefix + line for line in record.exc_text.rstrip("\n").split("\n"))

        if record.stack_info:
            lines.extend(prefix + line for line in record.stack_info.rstrip("\n").split("\n"))

        return "\n".join(lines)

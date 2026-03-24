"""Structured logging for SYSTEM-X bot."""
import logging
import sys
import threading
from pathlib import Path
from collections import deque
from datetime import datetime


class MemoryHandler(logging.Handler):
    def __init__(self, maxlen: int = 100):
        super().__init__()
        self.logs = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with self._lock:
                self.logs.append({
                    "time": datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
                    "level": record.levelname,
                    "message": msg,
                })
        except Exception:
            self.handleError(record)

    def get_logs(self, level: str | None = None, limit: int = 50) -> list[dict]:
        with self._lock:
            logs = list(self.logs)
        if level:
            logs = [l for l in logs if l["level"] == level]
        return logs[-limit:]


LOG_BUFFER: deque = deque(maxlen=200)


def setup_logging(log_path: str = "trading_bot/logs/bot.log") -> logging.Logger:
    log_dir = Path(log_path).parent
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o755)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    memory_handler = MemoryHandler(maxlen=200)
    memory_handler.setFormatter(formatter)
    memory_handler.setLevel(logging.DEBUG)

    logger = logging.getLogger("systemx")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(memory_handler)
    logger.propagate = False

    global LOG_BUFFER
    LOG_BUFFER = memory_handler.logs

    return logger


def get_recent_logs(level: str | None = None, limit: int = 50) -> list[dict]:
    logger = logging.getLogger("systemx")
    for h in logger.handlers:
        if isinstance(h, MemoryHandler):
            return h.get_logs(level, limit)
    return []


log = setup_logging()

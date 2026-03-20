"""Structured logging for SYSTEM-X bot."""
import logging
import sys
from pathlib import Path


def setup_logging(log_path: str = "/opt/systemx/logs/bot.log") -> logging.Logger:
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

    logger = logging.getLogger("systemx")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger


log = setup_logging()

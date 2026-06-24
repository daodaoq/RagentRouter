"""File-based logging with rotation for RAgent Router backend."""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# ── Formatters ────────────────────────────────────────────────────

FILE_FORMAT = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

CONSOLE_FORMAT = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """Configure root logger with file rotation and console output."""

    root = logging.getLogger("ragent")
    root.setLevel(level)
    root.handlers.clear()  # avoid duplicates on reload

    # ── File handler (10 MB × 5 backups) ──────────────────────
    log_file = os.path.join(LOG_DIR, "ragent.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(FILE_FORMAT)
    root.addHandler(file_handler)

    # ── Console handler ────────────────────────────────────────
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(CONSOLE_FORMAT)
    root.addHandler(console)

    # ── Separate routing log ───────────────────────────────────
    route_log = os.path.join(LOG_DIR, "routes.log")
    route_handler = RotatingFileHandler(
        route_log, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    route_handler.setLevel(logging.DEBUG)
    route_handler.setFormatter(FILE_FORMAT)
    route_logger = logging.getLogger("ragent.route")
    route_logger.handlers.clear()
    route_logger.addHandler(route_handler)
    route_logger.propagate = False  # don't duplicate to root

    # ── Request log ────────────────────────────────────────────
    req_log = os.path.join(LOG_DIR, "requests.log")
    req_handler = RotatingFileHandler(
        req_log, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    req_handler.setLevel(logging.DEBUG)
    req_handler.setFormatter(FILE_FORMAT)
    req_logger = logging.getLogger("ragent.request")
    req_logger.handlers.clear()
    req_logger.addHandler(req_handler)
    req_logger.propagate = False

    root.info("=" * 50)
    root.info("RAgent Router backend starting")
    root.info(f"Log directory: {LOG_DIR}")
    root.info(f"Log files: ragent.log, routes.log, requests.log")
    root.info("=" * 50)

    return root


# ── Convenience getters ───────────────────────────────────────────

def get_logger(name: str = "ragent") -> logging.Logger:
    return logging.getLogger(name)


def route_logger() -> logging.Logger:
    return logging.getLogger("ragent.route")


def request_logger() -> logging.Logger:
    return logging.getLogger("ragent.request")

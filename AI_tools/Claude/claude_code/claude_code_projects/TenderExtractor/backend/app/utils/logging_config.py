# logging_config.py
"""
One place to configure logging. Every module calls get_logger(__name__)
instead of using print(), so output is consistent and can be redirected
(e.g. to a file or a log aggregator) without touching pipeline code.
"""
import logging
import logging.handlers  # Required for RotatingFileHandler
import sys
from datetime import datetime
from pathlib import Path

from app import config

_CONFIGURED = False

MAX_LOG_BYTES = 1_000_000  # rotate once app.log exceeds ~1MB


def _ist_time(*_args):
    """
    logging.Formatter.converter replacement so log timestamps read as IST
    regardless of the host/container's system clock (typically UTC on
    cloud hosts, which "local time" would otherwise silently follow).
    """
    return datetime.now(config.IST).timetuple()


def get_logger(name: str) -> logging.Logger:
    global _CONFIGURED

    if not _CONFIGURED:
        log_file = config.LOG_FILE

        # Configure handlers dynamically
        handlers = [logging.StreamHandler(sys.stdout)]

        if log_file:
            # Ensure the parent logs directory exists to prevent FileNotFoundError
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Once app.log exceeds MAX_LOG_BYTES, it's renamed to
            # app.log.1 (overwriting any previous app.log.1) and logging
            # continues in a fresh app.log.
            file_handler = logging.handlers.RotatingFileHandler(
                filename=str(log_path),
                maxBytes=MAX_LOG_BYTES,
                backupCount=1,
                encoding="utf-8",
            )

            handlers.append(file_handler)

        logging.Formatter.converter = _ist_time

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s IST | %(levelname)-7s | %(name)s.%(funcName)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=handlers,
        )
        _CONFIGURED = True

    return logging.getLogger(name)

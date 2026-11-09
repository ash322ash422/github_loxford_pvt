"""
logging_config.py
------------------
INDUSTRY PATTERN: structured logging instead of print().

Production systems don't use print() -- they use structured logs
(one JSON object per line) so that logs can be shipped to a log
aggregator (Datadog, CloudWatch, ELK, etc.) and queried like data:
"show me every tool_call event where tool='apply_recommendation' and
status='error' in the last hour." That query is impossible against
scattered print() output but trivial against structured JSON logs.

This module gives every agent a logger that:
  - Tags every line with the agent's name (`extra={"agent": ...}`)
  - Emits one JSON object per line to stdout
  - Still reads fine in a terminal during development

In a real company this file would instead configure something like
`structlog`, or ship logs to an APM/tracing tool (e.g. via OpenTelemetry).
The shape -- structured, queryable, one place to configure it -- is the
part worth learning; the specific library is a swappable implementation
detail.
"""

import json
import logging
import sys

import config


class JsonFormatter(logging.Formatter):
    """Renders each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "agent": getattr(record, "agent", "system"),
            "message": record.getMessage(),
        }
        # Any extra structured fields passed via `extra={...}` get merged in,
        # e.g. logger.info("tool call", extra={"tool": "read_csv", "duration_ms": 12})
        for key, value in record.__dict__.items():
            if key not in payload and key not in (
                "args", "msg", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno",
                "funcName", "created", "msecs", "relativeCreated", "thread",
                "threadName", "processName", "process", "name",
            ):
                payload[key] = value
        return json.dumps(payload, default=str)


def get_logger(agent_name: str) -> logging.LoggerAdapter:
    """
    Returns a logger pre-tagged with the calling agent's name, e.g.:

        log = get_logger("DataAgent")
        log.info("fetched rows", extra={"row_count": 42})

    which emits:
        {"timestamp": "...", "level": "INFO", "agent": "DataAgent",
         "message": "fetched rows", "row_count": 42}
    """
    base_logger = logging.getLogger("agentic_pipeline")
    if not base_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        base_logger.addHandler(handler)
        base_logger.setLevel(config.LOG_LEVEL)
        base_logger.propagate = False

    return logging.LoggerAdapter(base_logger, {"agent": agent_name})

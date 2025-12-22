from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime

from opentelemetry import trace


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        ctx = span.get_span_context() if span is not None else None

        if ctx and ctx.is_valid:
            record.trace_id = f"{ctx.trace_id:032x}"
            record.span_id = f"{ctx.span_id:016x}"
        else:
            record.trace_id = None
            record.span_id = None

        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None),
            "span_id": getattr(record, "span_id", None),
        }

        reserved = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
        }

        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in reserved and k not in {"trace_id", "span_id"}
        }

        if extras:
            base.update(extras)

        return json.dumps(base, default=str)


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = os.getenv("LOG_FORMAT", "json").lower()

    root = logging.getLogger()
    root.setLevel(level)

    root.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(TraceContextFilter())

    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root.addHandler(handler)

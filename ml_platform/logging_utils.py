"""Structured logging helpers for ML Platform CLIs and steps."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any


def setup_logging(name: str = "ml_platform", level: int | None = None) -> logging.Logger:
    """Configure a JSON-friendly logger once and return it."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    resolved = level if level is not None else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(resolved)
    logger.propagate = False
    return logger


def log_json(logger: logging.Logger, message: str, **fields: Any) -> None:
    """Emit a single-line structured log entry."""
    payload = {"message": message, **fields}
    logger.info(json.dumps(payload, default=str, sort_keys=True))

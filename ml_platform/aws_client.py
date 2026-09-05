"""Shared boto3 client factory with production retry defaults."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.config import Config

_RETRY_CONFIG = Config(
    retries={"max_attempts": 10, "mode": "adaptive"},
    connect_timeout=5,
    read_timeout=60,
)


def client(service_name: str, region_name: str | None = None, **kwargs: Any):
    """Return a boto3 client with adaptive retries."""
    return boto3.client(service_name, region_name=region_name, config=_RETRY_CONFIG, **kwargs)

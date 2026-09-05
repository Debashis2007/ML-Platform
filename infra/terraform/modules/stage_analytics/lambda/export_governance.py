"""Export Stage Governance DynamoDB items to S3 JSON for Athena."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3

_DDB = None
_S3 = None


def _ddb():
    global _DDB
    if _DDB is None:
        _DDB = boto3.resource("dynamodb")
    return _DDB


def _s3():
    global _S3
    if _S3 is None:
        _S3 = boto3.client("s3")
    return _S3


def _json_default(obj: Any):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def handler(event, context):
    table_name = os.environ["GOVERNANCE_TABLE"]
    bucket = os.environ["EXPORT_BUCKET"]
    prefix = os.environ.get("EXPORT_PREFIX", "governance-export").rstrip("/")

    table = _ddb().Table(table_name)
    items: list[dict] = []
    scan_kwargs: dict[str, Any] = {}
    while True:
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    now = datetime.now(timezone.utc)
    key = f"{prefix}/dt={now.strftime('%Y-%m-%d')}/export-{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    body = "\n".join(json.dumps(item, default=_json_default) for item in items)
    _s3().put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/x-ndjson",
    )
    return {
        "statusCode": 200,
        "exported": len(items),
        "s3_uri": f"s3://{bucket}/{key}",
    }

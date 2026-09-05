#!/usr/bin/env python3
"""Start a SageMaker Pipeline execution (GHA → pipeline trigger)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from botocore.exceptions import ClientError

from ml_platform.aws_client import client as aws_client
from ml_platform.logging_utils import log_json, setup_logging

logger = setup_logging("ml_platform.run_pipeline")


def _client_token(pipeline_name: str, image_uri: str, data_uri: str, output_prefix: str) -> str:
    """Deterministic-ish token for a short window so retries are idempotent."""
    digest = hashlib.sha256(
        f"{pipeline_name}|{image_uri}|{data_uri}|{output_prefix}".encode()
    ).hexdigest()[:24]
    # Include hour bucket so intentional re-runs within a new hour still start.
    hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    return f"{hour}-{digest}"[:32]


def main() -> None:
    parser = argparse.ArgumentParser(description="Start SageMaker pipeline execution")
    parser.add_argument("--pipeline-name", required=True)
    parser.add_argument("--role-arn", required=True, help="Accepted for CLI parity; SageMaker uses pipeline role")
    parser.add_argument("--image-uri", required=True)
    parser.add_argument("--data-uri", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--region", default=None)
    parser.add_argument("--wait", action="store_true", help="Poll until pipeline execution finishes")
    parser.add_argument("--wait-seconds", type=int, default=3600)
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()

    sm = aws_client("sagemaker", region_name=args.region)
    display_name = f"{args.pipeline_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    client_token = _client_token(args.pipeline_name, args.image_uri, args.data_uri, args.output_prefix)

    try:
        response = sm.start_pipeline_execution(
            PipelineName=args.pipeline_name,
            PipelineExecutionDisplayName=display_name,
            ClientRequestToken=client_token,
            PipelineParameters=[
                {"Name": "ImageUri", "Value": args.image_uri},
                {"Name": "DataUri", "Value": args.data_uri},
                {"Name": "OutputPrefix", "Value": args.output_prefix},
            ],
        )
    except ClientError as exc:
        logger.error("start_pipeline_execution failed: %s", exc)
        raise SystemExit(1) from exc

    arn = response.get("PipelineExecutionArn")
    if not arn:
        raise SystemExit("PipelineExecutionArn missing from response")

    log_json(
        logger,
        "pipeline_execution_started",
        pipeline_name=args.pipeline_name,
        pipeline_execution_arn=arn,
        display_name=display_name,
        client_request_token=client_token,
        role_arn=args.role_arn,
    )
    print(json.dumps({"PipelineExecutionArn": arn, "PipelineExecutionDisplayName": display_name}, default=str))

    if not args.wait:
        return

    deadline = time.monotonic() + args.wait_seconds
    terminal = {"Succeeded", "Failed", "Stopped"}
    status = "Executing"
    while time.monotonic() < deadline:
        desc = sm.describe_pipeline_execution(PipelineExecutionArn=arn)
        status = desc.get("PipelineExecutionStatus", "Unknown")
        log_json(logger, "pipeline_execution_status", arn=arn, status=status)
        if status in terminal:
            break
        time.sleep(max(5, args.poll_seconds))

    if status != "Succeeded":
        logger.error("Pipeline execution ended with status=%s arn=%s", status, arn)
        raise SystemExit(1)
    log_json(logger, "pipeline_execution_succeeded", arn=arn)


if __name__ == "__main__":
    main()

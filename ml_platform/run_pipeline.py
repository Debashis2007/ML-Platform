#!/usr/bin/env python3
"""Start a SageMaker Pipeline execution in the configured training account."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from ml_platform.config import ModelConfig
from ml_platform.logging_utils import log_json, setup_logging

logger = setup_logging("ml_platform.run_pipeline")


def _client_token(pipeline_name: str, image_uri: str, data_uri: str, output_prefix: str, source_commit: str) -> str:
    """Deterministic token for a short window so retries are idempotent."""
    digest = hashlib.sha256(
        f"{pipeline_name}|{image_uri}|{data_uri}|{output_prefix}|{source_commit}".encode()
    ).hexdigest()[:24]
    # Include hour bucket so intentional re-runs within a new hour still start.
    hour = datetime.now(timezone.utc).strftime("%Y%m%d%H")
    return f"{hour}-{digest}"[:32]


def pipeline_parameters(
    image_uri: str,
    data_uri: str,
    output_prefix: str,
    source_commit: str,
    lineage_source_package_arn: str = "",
    submitted_by: str = "",
) -> list[dict[str, str]]:
    if "@sha256:" not in image_uri:
        raise ValueError("--image-uri must be pinned by digest (repo@sha256:...), never a tag")
    if not source_commit:
        raise ValueError("--source-commit is required for lineage")
    return [
        {"Name": "ImageUri", "Value": image_uri},
        {"Name": "DataUri", "Value": data_uri},
        {"Name": "OutputPrefix", "Value": output_prefix},
        {"Name": "SourceCommit", "Value": source_commit},
        {"Name": "SubmittedBy", "Value": submitted_by},
        {"Name": "LineageSourcePackageArn", "Value": lineage_source_package_arn},
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Start SageMaker pipeline execution")
    parser.add_argument("--config", required=True, help="Path to model.yaml")
    parser.add_argument("--stage", choices=["nonprod", "prod"], default="nonprod",
                        help="prod = retrain in the Prod control plane (aws.prod)")
    parser.add_argument("--image-uri", required=True, help="Model image pinned by digest")
    parser.add_argument("--data-uri", default=None, help="Defaults to data.train_uri")
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--lineage-source-package-arn", default="",
                        help="NonProd package ARN when this is a Prod retrain")
    parser.add_argument("--submitted-by", default=os.environ.get("GITHUB_ACTOR", ""),
                        help="Identity that triggered training; the approver must differ")
    parser.add_argument("--wait", action="store_true", help="Poll until pipeline execution finishes")
    parser.add_argument("--wait-seconds", type=int, default=3600)
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()

    cfg = ModelConfig.load(args.config, stage=args.stage)
    data_uri = args.data_uri or cfg.train_uri or ""
    try:
        params = pipeline_parameters(
            args.image_uri, data_uri, args.output_prefix, args.source_commit,
            args.lineage_source_package_arn, args.submitted_by,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    caller = aws_client("sts", region_name=cfg.region).get_caller_identity()["Account"]
    if caller != cfg.account_id:
        raise SystemExit(f"Caller account {caller} does not match aws.account_id {cfg.account_id}")

    sm = aws_client("sagemaker", region_name=cfg.region)
    pipeline_name = cfg.pipeline_name
    display_name = f"{cfg.model_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    client_token = _client_token(pipeline_name, args.image_uri, data_uri, args.output_prefix, args.source_commit)

    try:
        response = sm.start_pipeline_execution(
            PipelineName=pipeline_name,
            PipelineExecutionDisplayName=display_name,
            ClientRequestToken=client_token,
            PipelineParameters=params,
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
        pipeline_name=pipeline_name,
        pipeline_execution_arn=arn,
        display_name=display_name,
        client_request_token=client_token,
        training_target=cfg.training_target,
        account_id=cfg.account_id,
        source_commit=args.source_commit,
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

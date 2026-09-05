#!/usr/bin/env python3
"""Register model package in SageMaker Model Registry (PendingManualApproval)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def _find_model_artifact(model_dir: Path) -> Path | None:
    for name in ("model.tar.gz", "model.joblib"):
        candidate = model_dir / name
        if candidate.is_file():
            return candidate
    matches = list(model_dir.rglob("model.joblib"))
    return matches[0] if matches else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="/opt/ml/processing/model")
    parser.add_argument("--model-package-group", default=os.environ.get("MODEL_PACKAGE_GROUP", "ModelCreditRisk"))
    parser.add_argument("--inference-image-uri", default=os.environ.get("INFERENCE_IMAGE_URI", ""))
    parser.add_argument("--model-data-url", default=os.environ.get("MODEL_DATA_URL", ""))
    parser.add_argument("--model-name", default=os.environ.get("MODEL_NAME", "credit-risk"))
    parser.add_argument(
        "--approval-status",
        default=os.environ.get("MODEL_APPROVAL_STATUS", "PendingManualApproval"),
    )
    parser.add_argument(
        "--life-cycle-stage",
        default=os.environ.get("MODEL_LIFE_CYCLE_STAGE", "Development"),
        help="Model Registry staging construct stage (e.g. Development, PreProduction, Production).",
    )
    parser.add_argument(
        "--life-cycle-status",
        default=os.environ.get("MODEL_LIFE_CYCLE_STATUS", "PendingApproval"),
        help="Model Registry staging construct status (e.g. PendingApproval, Approved).",
    )
    parser.add_argument("--region", default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"))
    args, _unknown = parser.parse_known_args()

    image_uri = args.inference_image_uri.strip()
    model_data_url = args.model_data_url.strip()
    if not image_uri:
        raise SystemExit("INFERENCE_IMAGE_URI / --inference-image-uri is required")
    if not model_data_url:
        # Fallback: some jobs only mount extracted artifacts; require explicit S3 URI in pipeline.
        artifact = _find_model_artifact(Path(args.model_dir))
        raise SystemExit(
            "MODEL_DATA_URL / --model-data-url (s3://.../model.tar.gz) is required. "
            f"Local artifact present={bool(artifact)}"
        )

    sm = boto3.client(
        "sagemaker",
        region_name=args.region,
        config=Config(retries={"max_attempts": 8, "mode": "adaptive"}),
    )
    request = {
        "ModelPackageGroupName": args.model_package_group,
        "ModelPackageDescription": f"{args.model_name} registered by ML Platform pipeline",
        "ModelApprovalStatus": args.approval_status,
        "ModelLifeCycle": {
            "Stage": args.life_cycle_stage,
            "StageStatus": args.life_cycle_status,
            "StageDescription": f"{args.model_name} pipeline registration",
        },
        "InferenceSpecification": {
            "Containers": [
                {
                    "Image": image_uri,
                    "ModelDataUrl": model_data_url,
                    "Environment": {"MODEL_NAME": args.model_name},
                }
            ],
            "SupportedContentTypes": ["application/json"],
            "SupportedResponseMIMETypes": ["application/json"],
            "SupportedRealtimeInferenceInstanceTypes": ["ml.m5.large", "ml.m5.xlarge"],
            "SupportedTransformInstanceTypes": ["ml.m5.large", "ml.m5.xlarge"],
        },
        "CustomerMetadataProperties": {
            "model_name": args.model_name,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    try:
        response = sm.create_model_package(**request)
    except ClientError as exc:
        raise SystemExit(f"create_model_package failed: {exc}") from exc

    record = {
        "model_package_arn": response.get("ModelPackageArn"),
        "model_package_group_name": args.model_package_group,
        "model_approval_status": args.approval_status,
        "inference_specification": request["InferenceSpecification"],
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(record, indent=2, default=str))


if __name__ == "__main__":
    main()

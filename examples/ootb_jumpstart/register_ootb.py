#!/usr/bin/env python3
"""Register an out-of-the-box SageMaker JumpStart model into Model Registry.

No custom train/Docker required. Use this for a first endpoint smoke test, then
swap to examples/credit-risk for the full Train→Evaluate→Register pipeline.

Examples:
  python examples/ootb_jumpstart/register_ootb.py \\
    --model-package-group ModelOotbDemo \\
    --role-arn arn:aws:iam::ACCOUNT:role/mlp-sagemaker-pipeline

  # Optional: auto-approve for Non-Prod smoke only
  python examples/ootb_jumpstart/register_ootb.py ... --approval-status Approved
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


DEFAULT_MODEL_ID = "xgboost-classification-model"


def main() -> None:
    parser = argparse.ArgumentParser(description="Register JumpStart OOTB model")
    parser.add_argument(
        "--model-id",
        default=os.environ.get("JUMPSTART_MODEL_ID", DEFAULT_MODEL_ID),
        help="SageMaker JumpStart model id (tabular XGBoost by default).",
    )
    parser.add_argument(
        "--model-package-group",
        default=os.environ.get("MODEL_PACKAGE_GROUP", "ModelOotbDemo"),
    )
    parser.add_argument(
        "--role-arn",
        default=os.environ.get("SAGEMAKER_PIPELINE_ROLE_ARN")
        or os.environ.get("MLP_PIPELINE_ROLE_ARN", ""),
        help="Execution role ARN used by JumpStart for packaging (client-managed).",
    )
    parser.add_argument(
        "--approval-status",
        default=os.environ.get("MODEL_APPROVAL_STATUS", "PendingManualApproval"),
        choices=["PendingManualApproval", "Approved", "Rejected"],
    )
    parser.add_argument(
        "--life-cycle-stage",
        default=os.environ.get("MODEL_LIFE_CYCLE_STAGE", "Development"),
    )
    parser.add_argument(
        "--life-cycle-status",
        default=os.environ.get("MODEL_LIFE_CYCLE_STATUS", "PendingApproval"),
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    )
    parser.add_argument(
        "--instance-type",
        default=os.environ.get("JUMPSTART_INSTANCE_TYPE", "ml.m5.large"),
        help="Preferred realtime instance type recorded on the package.",
    )
    args = parser.parse_args()

    if not args.role_arn:
        raise SystemExit("--role-arn / SAGEMAKER_PIPELINE_ROLE_ARN is required")

    os.environ.setdefault("AWS_DEFAULT_REGION", args.region)
    os.environ.setdefault("AWS_REGION", args.region)

    # Ensure package group exists (idempotent).
    sm = boto3.client(
        "sagemaker",
        region_name=args.region,
        config=Config(retries={"max_attempts": 8, "mode": "adaptive"}),
    )
    try:
        sm.create_model_package_group(
            ModelPackageGroupName=args.model_package_group,
            ModelPackageGroupDescription="OOTB JumpStart models for platform smoke tests",
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {
            "ValidationException",
            "ResourceInUse",
        }:
            # Already exists often returns ValidationException with "already exists"
            msg = str(exc)
            if "already exists" not in msg.lower() and "Cannot create" not in msg:
                raise

    from sagemaker.jumpstart.model import JumpStartModel
    from sagemaker.session import Session

    session = Session(boto_session=boto3.Session(region_name=args.region))
    js_model = JumpStartModel(
        model_id=args.model_id,
        role=args.role_arn,
        sagemaker_session=session,
        instance_type=args.instance_type,
    )

    # JumpStart.register returns a ModelPackage / ModelPackageModel depending on SDK.
    registered = js_model.register(
        model_package_group_name=args.model_package_group,
        approval_status=args.approval_status,
        content_types=["text/csv", "application/json"],
        response_types=["text/csv", "application/json"],
        inference_instances=[args.instance_type, "ml.m5.xlarge"],
        transform_instances=[args.instance_type],
    )

    package_arn = getattr(registered, "model_package_arn", None) or getattr(
        registered, "arn", None
    )
    if not package_arn and hasattr(registered, "describe"):
        package_arn = registered.describe().get("ModelPackageArn")
    if not package_arn:
        # Fallback: latest package in group
        listing = sm.list_model_packages(
            ModelPackageGroupName=args.model_package_group,
            SortBy="CreationTime",
            SortOrder="Descending",
            MaxResults=1,
        )
        package_arn = listing["ModelPackageSummaryList"][0]["ModelPackageArn"]

    # Apply staging construct metadata when API supports it.
    try:
        sm.update_model_package(
            ModelPackageArn=package_arn,
            ModelApprovalStatus=args.approval_status,
            ModelLifeCycle={
                "Stage": args.life_cycle_stage,
                "StageStatus": args.life_cycle_status
                if args.approval_status != "Approved"
                else "Approved",
                "StageDescription": f"OOTB JumpStart {args.model_id}",
            },
            CustomerMetadataProperties={
                "source": "jumpstart",
                "jumpstart_model_id": args.model_id,
                "registered_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except ClientError as exc:
        # Older accounts / regions may reject ModelLifeCycle; approval still set via register.
        print(json.dumps({"warning": f"update_model_package partial: {exc}"}))

    record = {
        "model_package_arn": package_arn,
        "model_package_group_name": args.model_package_group,
        "jumpstart_model_id": args.model_id,
        "model_approval_status": args.approval_status,
        "next_steps": [
            "Approve in Model Registry if still PendingManualApproval",
            "Approve through the management API, then release with ml-lifecycle.yml (release phase)",
            "Set TF_VAR_model_package_arn / SSM to this ARN",
        ],
    }
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()

"""Promote an approved Non-Prod model package into the Prod Model Registry."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_CONFIG = Config(retries={"max_attempts": 8, "mode": "adaptive"})
_SM = None
_SSM = None
_EVENTS = None


def _sm():
    global _SM
    if _SM is None:
        _SM = boto3.client("sagemaker", config=_CONFIG)
    return _SM


def _ssm():
    global _SSM
    if _SSM is None:
        _SSM = boto3.client("ssm", config=_CONFIG)
    return _SSM


def _events():
    global _EVENTS
    if _EVENTS is None:
        _EVENTS = boto3.client("events", config=_CONFIG)
    return _EVENTS


def _detail(event: dict[str, Any]) -> dict[str, Any]:
    detail = event.get("detail") or event
    if isinstance(detail, str):
        detail = json.loads(detail)
    return detail


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Copy Non-Prod approved package into Prod package group and signal deploy.

    Expected env:
      TARGET_MODEL_PACKAGE_GROUP
      DEPLOY_PARAMETER_PREFIX
      TARGET_APPROVAL_STATUS (default Approved)
    Event detail must include model_package_arn (source).
    """
    detail = _detail(event)
    source_arn = detail.get("model_package_arn") or detail.get("ModelPackageArn") or event.get("source_model_package_arn")
    if not source_arn:
        raise ValueError("source model_package_arn is required")

    target_group = os.environ["TARGET_MODEL_PACKAGE_GROUP"]
    deploy_prefix = os.environ.get("DEPLOY_PARAMETER_PREFIX", "/mlp/deploy").rstrip("/")
    approval = os.environ.get("TARGET_APPROVAL_STATUS", "Approved")
    business_unit = (
        detail.get("business_unit")
        or event.get("business_unit")
        or os.environ.get("BUSINESS_UNIT", "")
    )
    life_stage = os.environ.get("MODEL_LIFE_CYCLE_STAGE", "Production")
    life_status = os.environ.get("MODEL_LIFE_CYCLE_STATUS", "Approved")

    sm = _sm()
    source = sm.describe_model_package(ModelPackageName=source_arn)
    inference = source.get("InferenceSpecification")
    if not inference:
        raise ValueError(f"Source package has no InferenceSpecification: {source_arn}")

    request: dict[str, Any] = {
        "ModelPackageGroupName": target_group,
        "ModelPackageDescription": (
            f"Promoted from {source_arn}"
            + (f" for BU {business_unit}" if business_unit else "")
        ),
        "ModelApprovalStatus": approval,
        "ModelLifeCycle": {
            "Stage": life_stage,
            "StageStatus": life_status,
            "StageDescription": f"Promoted from {source_arn}",
        },
        "InferenceSpecification": inference,
    }
    if source.get("CustomerMetadataProperties"):
        meta = dict(source["CustomerMetadataProperties"])
        meta["promoted_from"] = source_arn
        if business_unit:
            meta["business_unit"] = business_unit
        request["CustomerMetadataProperties"] = meta
    elif business_unit:
        request["CustomerMetadataProperties"] = {
            "promoted_from": source_arn,
            "business_unit": business_unit,
        }

    try:
        resp = sm.create_model_package(**request)
    except ClientError as exc:
        logger.error("create_model_package failed: %s", exc)
        raise

    promoted_arn = resp["ModelPackageArn"]
    ssm_names = [f"{deploy_prefix}/model_package_arn", f"{deploy_prefix}/{target_group}/model_package_arn"]
    if business_unit:
        ssm_names.append(f"{deploy_prefix}/{business_unit}/model_package_arn")

    for name in ssm_names:
        _ssm().put_parameter(Name=name, Value=promoted_arn, Type="String", Overwrite=True)

    put = _events().put_events(
        Entries=[
            {
                "Source": "ml.platform.promote",
                "DetailType": "Model Promoted",
                "Detail": json.dumps(
                    {
                        "source_model_package_arn": source_arn,
                        "model_package_arn": promoted_arn,
                        "model_package_group": target_group,
                        "business_unit": business_unit,
                        "approval_status": approval,
                    }
                ),
            }
        ]
    )
    if put.get("FailedEntryCount", 0):
        raise RuntimeError(f"EventBridge FailedEntryCount={put.get('FailedEntryCount')}")

    body = {
        "source_model_package_arn": source_arn,
        "promoted_model_package_arn": promoted_arn,
        "model_package_group": target_group,
        "business_unit": business_unit,
    }
    logger.info("model_promoted %s", json.dumps(body))
    return {"statusCode": 200, "body": json.dumps(body)}


handler = lambda_handler

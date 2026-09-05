"""Capture SageMaker Model Package approval events for governance / deploy."""

from __future__ import annotations

import json
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_CONFIG = Config(retries={"max_attempts": 8, "mode": "adaptive"})
_DDB = None
_SSM = None
_EVENTS = None


def _ddb():
    global _DDB
    if _DDB is None:
        _DDB = boto3.resource("dynamodb", config=_CONFIG)
    return _DDB


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


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Capture Model Package state change → DynamoDB; publish deploy signal on Approved.

    Registry approval → EventBridge → Lambda → DynamoDB → Workflow B.
    """
    request_id = getattr(context, "aws_request_id", None)
    detail = event.get("detail", event) or {}
    table_name = os.environ.get("GOVERNANCE_TABLE", "MLPlatformStageGovernance")
    deploy_prefix = os.environ.get("DEPLOY_PARAMETER_PREFIX", "/mlp/deploy").rstrip("/")

    group = str(detail.get("ModelPackageGroupName") or "unknown")
    version = str(detail.get("ModelPackageVersion") or datetime.now(timezone.utc).isoformat())
    package_arn = str(detail.get("ModelPackageArn") or "")
    approval_status = detail.get("ModelApprovalStatus")
    business_unit = str(
        detail.get("BusinessUnit")
        or os.environ.get("BUSINESS_UNIT", "")
        or ""
    )

    record = {
        "pk": group,
        "sk": version,
        "model_package_arn": package_arn,
        "approval_status": approval_status,
        "business_unit": business_unit,
        "account": event.get("account", ""),
        "region": event.get("region", ""),
        "source": event.get("source", "aws.sagemaker"),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id or "",
        "raw": json.dumps(detail, default=str)[:3500],
    }

    try:
        _ddb().Table(table_name).put_item(Item=record)
        logger.info(
            "governance_recorded group=%s version=%s status=%s request_id=%s",
            group,
            version,
            approval_status,
            request_id,
        )
    except ClientError as exc:
        logger.error("DynamoDB put_item failed: %s\n%s", exc, traceback.format_exc())
        raise

    if approval_status == "Approved" and package_arn:
        params = [
            f"{deploy_prefix}/{group}/model_package_arn",
            f"{deploy_prefix}/model_package_arn",
        ]
        for name in params:
            try:
                _ssm().put_parameter(Name=name, Value=package_arn, Type="String", Overwrite=True)
            except ClientError as exc:
                logger.error("SSM put_parameter failed name=%s error=%s", name, exc)
                raise

        try:
            put = _events().put_events(
                Entries=[
                    {
                        "Source": "ml.platform.governance",
                        "DetailType": "Model Approved",
                    "Detail": json.dumps(
                        {
                            "model_package_arn": package_arn,
                            "model_package_group": group,
                            "model_package_version": version,
                            "business_unit": business_unit,
                            "request_id": request_id,
                        }
                    ),
                }
                ]
            )
            failed = put.get("FailedEntryCount", 0)
            if failed:
                logger.error("EventBridge put_events failed entries=%s", put.get("Entries"))
                raise RuntimeError(f"EventBridge FailedEntryCount={failed}")
        except ClientError as exc:
            logger.error("EventBridge put_events ClientError: %s", exc)
            raise

        logger.info(
            "deploy_signal_published group=%s arn=%s request_id=%s",
            group,
            package_arn,
            request_id,
        )

    return {"statusCode": 200, "body": json.dumps(record, default=str)}


handler = lambda_handler

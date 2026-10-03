"""Capture SageMaker Model Package state changes into the decision log.

An Approved state is honoured only when it carries an approval_id written by the
management API and the lifecycle record agrees. A console or CLI approval without
that binding is logged as APPROVAL_VIOLATION and never produces a deploy signal.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
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
_SM = None


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


def _sm():
    global _SM
    if _SM is None:
        _SM = boto3.client("sagemaker", config=_CONFIG)
    return _SM


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _put_event(detail_type: str, detail: dict[str, Any]) -> None:
    put = _events().put_events(
        Entries=[{"Source": "ml.platform.governance", "DetailType": detail_type,
                  "Detail": json.dumps(detail, default=str)}]
    )
    if put.get("FailedEntryCount", 0):
        logger.error("EventBridge put_events failed entries=%s", put.get("Entries"))
        raise RuntimeError(f"EventBridge FailedEntryCount={put.get('FailedEntryCount')}")


def _metadata(detail: dict[str, Any], package_arn: str) -> dict[str, str]:
    meta = detail.get("CustomerMetadataProperties")
    if meta is None and package_arn:
        meta = _sm().describe_model_package(ModelPackageName=package_arn).get("CustomerMetadataProperties")
    return dict(meta or {})


def api_approval_is_bound(meta: dict[str, str]) -> bool:
    """True when the lifecycle record shows this exact approval came through the management API."""
    approval_id = meta.get("approval_id")
    if not approval_id or not meta.get("tenant_id") or not meta.get("model_data_sha256"):
        return False
    record = _ddb().Table(os.environ["LIFECYCLE_TABLE"]).get_item(
        Key={"pk": f"{meta['tenant_id']}#{meta['model_id']}", "sk": f"PKG#{meta['model_data_sha256']}"}
    ).get("Item") or {}
    return (
        record.get("approval_id") == approval_id
        and record.get("state") == "APPROVED"
        and record.get("canonical_hash") == meta.get("canonical_hash") == meta.get("approval_hash")
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", None) or ""
    detail = event.get("detail", event) or {}
    deploy_prefix = os.environ.get("DEPLOY_PARAMETER_PREFIX", "/mlp/deploy").rstrip("/")

    group = str(detail.get("ModelPackageGroupName") or "unknown")
    version = str(detail.get("ModelPackageVersion") or "")
    package_arn = str(detail.get("ModelPackageArn") or "")
    approval_status = str(detail.get("ModelApprovalStatus") or "")
    meta = _metadata(detail, package_arn)
    model_key = f"{meta.get('tenant_id', 'unknown')}#{meta.get('model_id', group)}"

    action = f"STATE_{approval_status.upper() or 'UNKNOWN'}"
    deploy = False
    if approval_status == "Approved":
        if api_approval_is_bound(meta):
            action, deploy = "APPROVAL_CONFIRMED", True
        else:
            action = "APPROVAL_VIOLATION"

    record = {
        "pk": model_key,
        "sk": f"{_now()}#{uuid.uuid4().hex}",
        "action": action,
        "actor": "capture_approval_event",
        "model_package_arn": package_arn,
        "model_package_group": group,
        "model_package_version": version,
        "approval_status": approval_status,
        "approval_id": meta.get("approval_id", ""),
        "account": event.get("account", ""),
        "region": event.get("region", ""),
        "request_id": request_id,
    }
    try:
        _ddb().Table(os.environ["DECISION_LOG_TABLE"]).put_item(Item={k: v for k, v in record.items() if v != ""})
    except ClientError as exc:
        logger.error("decision log put_item failed: %s", exc)
        raise

    if action == "APPROVAL_VIOLATION":
        logger.error("approval_violation package=%s (approved outside the management API)", package_arn)
        _put_event("Model Approval Violation", {"model_package_arn": package_arn, "model_package_group": group,
                                                "tenant_id": meta.get("tenant_id"), "request_id": request_id})

    if deploy:
        for name in (f"{deploy_prefix}/{group}/model_package_arn", f"{deploy_prefix}/model_package_arn"):
            _ssm().put_parameter(Name=name, Value=package_arn, Type="String", Overwrite=True)
        _put_event("Model Approved", {
            "model_package_arn": package_arn,
            "model_package_group": group,
            "model_package_version": version,
            "tenant_id": meta.get("tenant_id"),
            "model_id": meta.get("model_id"),
            "approval_id": meta.get("approval_id"),
            "canonical_hash": meta.get("canonical_hash"),
            "request_id": request_id,
        })
        logger.info("deploy_signal_published group=%s arn=%s", group, package_arn)

    return {"statusCode": 200, "body": json.dumps(record, default=str)}


handler = lambda_handler

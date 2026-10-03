"""Record a NonProd → Prod promotion request (design v7: copy by digest, retrain in Prod).

This Lambda never creates or approves a Prod package. It verifies that:
  * the NonProd package is Approved through the management API (approval_id present),
  * the image digest has already been copied into the Prod ECR repository,
then records PROMOTION_REQUESTED and emits an event. The workflow starts the Prod
pipeline with LineageSourcePackageArn; the Prod registration Lambda creates a
PendingManualApproval package that a Prod senior data scientist approves.
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
_CLIENTS: dict[str, Any] = {}


def _client(name: str) -> Any:
    if name not in _CLIENTS:
        _CLIENTS[name] = boto3.client(name, config=_CONFIG)
    return _CLIENTS[name]


def _sm():
    return _client("sagemaker")


def _ecr():
    return _client("ecr")


def _events():
    return _client("events")


def _ddb():
    if "ddb" not in _CLIENTS:
        _CLIENTS["ddb"] = boto3.resource("dynamodb", config=_CONFIG)
    return _CLIENTS["ddb"]


def _source_sm():
    """SageMaker client for the NonProd registry (read-only role when cross-account)."""
    role_arn = os.environ.get("SOURCE_REGISTRY_READ_ROLE_ARN", "")
    if not role_arn:
        return _sm()
    creds = _client("sts").assume_role(RoleArn=role_arn, RoleSessionName="ml-promote-read",
                                       DurationSeconds=900)["Credentials"]
    return boto3.client(
        "sagemaker",
        config=_CONFIG,
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def _detail(event: dict[str, Any]) -> dict[str, Any]:
    detail = event.get("detail") or event
    if isinstance(detail, str):
        detail = json.loads(detail)
    return detail


def _split_digest_uri(uri: str) -> tuple[str, str, str]:
    """123.dkr.ecr.region.amazonaws.com/repo@sha256:abc -> (registry_id, repo, digest)."""
    if "@sha256:" not in uri:
        raise ValueError("prod_image_uri must be pinned by digest (repo@sha256:...)")
    host_repo, digest = uri.split("@", 1)
    host, _, repo = host_repo.partition("/")
    return host.split(".", 1)[0], repo, digest


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    detail = _detail(event)
    source_arn = (detail.get("source_model_package_arn") or detail.get("model_package_arn")
                  or detail.get("ModelPackageArn"))
    if not source_arn:
        raise ValueError("source model_package_arn is required")
    prod_image_uri = str(detail.get("prod_image_uri") or "")
    registry_id, repo, digest = _split_digest_uri(prod_image_uri)

    source = _source_sm().describe_model_package(ModelPackageName=source_arn)
    if source.get("ModelApprovalStatus") != "Approved":
        raise ValueError(f"source package is {source.get('ModelApprovalStatus')}, not Approved")
    meta = source.get("CustomerMetadataProperties") or {}
    if not meta.get("approval_id"):
        raise ValueError("source package was not approved through the management API")
    source_image = source["InferenceSpecification"]["Containers"][0]["Image"]
    if source_image.split("@", 1)[-1] != digest:
        raise ValueError("prod_image_uri digest differs from the NonProd approved image digest")

    try:
        _ecr().describe_images(registryId=registry_id, repositoryName=repo, imageIds=[{"imageDigest": digest}])
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"ImageNotFoundException", "RepositoryNotFoundException"}:
            raise ValueError(f"digest {digest} not present in Prod ECR {repo}; copy it by digest first") from exc
        raise

    model_key = f"{meta.get('tenant_id', 'unknown')}#{meta.get('model_id', 'unknown')}"
    request_id = uuid.uuid4().hex
    _ddb().Table(os.environ["DECISION_LOG_TABLE"]).put_item(Item={
        "pk": model_key,
        "sk": f"{datetime.now(timezone.utc).isoformat()}#{request_id}",
        "action": "PROMOTION_REQUESTED",
        "actor": str(detail.get("requested_by") or "promote_model_package"),
        "source_model_package_arn": source_arn,
        "source_approval_id": meta["approval_id"],
        "prod_image_uri": prod_image_uri,
        "source_commit": meta.get("source_commit", ""),
    })

    body = {
        "promotion_request_id": request_id,
        "source_model_package_arn": source_arn,
        "prod_image_uri": prod_image_uri,
        "target_model_package_group": os.environ.get("TARGET_MODEL_PACKAGE_GROUP", ""),
        "tenant_id": meta.get("tenant_id"),
        "model_id": meta.get("model_id"),
        "source_commit": meta.get("source_commit"),
    }
    put = _events().put_events(Entries=[{
        "Source": "ml.platform.promote",
        "DetailType": "Model Promotion Requested",
        "Detail": json.dumps(body),
    }])
    if put.get("FailedEntryCount", 0):
        raise RuntimeError(f"EventBridge FailedEntryCount={put.get('FailedEntryCount')}")

    logger.info("promotion_requested %s", json.dumps(body))
    return {"statusCode": 200, "body": json.dumps(body)}


handler = lambda_handler

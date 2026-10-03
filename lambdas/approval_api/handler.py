"""Management API approval handler — the only path that approves a model package.

Routes (private REST API, Okta TOKEN authorizer):
  GET  /approvals?model_package_arn=...   package, lifecycle state and canonical hash
  POST /approvals                          {"model_package_arn", "decision": "approve"|"reject",
                                            "canonical_hash", "comment"}

Approve checks, in order: approver identity and role, tenant scope, separation of
duties, a lock with TTL and fencing, and the hash binding (request hash = package
metadata hash = lifecycle hash). Only then is the package status changed.
"""

from __future__ import annotations

import json
import logging
import os
import time
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

APPROVER_ROLE = "senior_data_scientist"
DECISIONS = {"approve": "Approved", "reject": "Rejected"}


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _sm() -> Any:
    if "sm" not in _CLIENTS:
        _CLIENTS["sm"] = boto3.client("sagemaker", config=_CONFIG)
    return _CLIENTS["sm"]


def _table(env_name: str) -> Any:
    if "ddb" not in _CLIENTS:
        _CLIENTS["ddb"] = boto3.resource("dynamodb", config=_CONFIG)
    return _CLIENTS["ddb"].Table(os.environ[env_name])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(body, default=str)}


def _caller(event: dict[str, Any]) -> dict[str, str]:
    auth = (event.get("requestContext") or {}).get("authorizer") or {}
    email = str(auth.get("email") or "").strip().lower()
    if not email:
        raise ApiError(401, "authorizer context has no email claim")
    return {"email": email, "sub": str(auth.get("principalId") or auth.get("sub") or "")}


def _package(arn: str) -> dict[str, Any]:
    try:
        return _sm().describe_model_package(ModelPackageName=arn)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"ValidationException", "ResourceNotFound"}:
            raise ApiError(404, "model package not found") from exc
        raise


def _lifecycle_key(meta: dict[str, str]) -> dict[str, str]:
    for field in ("tenant_id", "model_id", "model_data_sha256", "canonical_hash"):
        if not meta.get(field):
            raise ApiError(409, f"package metadata missing {field}; not registered by the platform")
    return {"pk": f"{meta['tenant_id']}#{meta['model_id']}", "sk": f"PKG#{meta['model_data_sha256']}"}


def log_decision(model_key: str, action: str, actor: str, **fields: Any) -> str:
    decision_id = uuid.uuid4().hex
    item = {"pk": model_key, "sk": f"{_now()}#{decision_id}", "action": action, "actor": actor,
            "decision_id": decision_id}
    item.update({k: v for k, v in fields.items() if v not in (None, "")})
    _table("DECISION_LOG_TABLE").put_item(Item=item)
    return decision_id


def check_identity(email: str, tenant_id: str) -> dict[str, Any]:
    identity = _table("IDENTITY_TABLE").get_item(Key={"pk": email}).get("Item")
    if not identity or identity.get("status", "active") != "active":
        raise ApiError(403, "approver is not an active platform identity")
    roles = set(identity.get("roles") or [])
    if APPROVER_ROLE not in roles:
        raise ApiError(403, f"approver lacks the {APPROVER_ROLE} role")
    tenants = set(identity.get("tenants") or [])
    if tenant_id not in tenants and "*" not in tenants:
        raise ApiError(403, f"approver is not scoped to tenant {tenant_id}")
    return identity


def check_separation_of_duties(identity: dict[str, Any], email: str, submitted_by: str) -> None:
    if not submitted_by:
        return
    own = {email, str(identity.get("github_login") or "").lower()} - {""}
    if submitted_by.lower() in own:
        raise ApiError(403, "separation of duties: the submitter cannot approve their own model")


def acquire_lock(key: str, owner: str) -> int:
    ttl = int(os.environ.get("LOCK_TTL_SECONDS", "120"))
    now = int(time.time())
    fence = time.time_ns()
    try:
        _table("LOCKS_TABLE").put_item(
            Item={"pk": key, "owner": owner, "fence": fence, "expires_at": now + ttl},
            ConditionExpression="attribute_not_exists(pk) OR expires_at < :now",
            ExpressionAttributeValues={":now": now},
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            raise ApiError(409, "another decision for this package is in progress") from exc
        raise
    return fence


def release_lock(key: str, fence: int) -> None:
    try:
        _table("LOCKS_TABLE").delete_item(
            Key={"pk": key}, ConditionExpression="fence = :f", ExpressionAttributeValues={":f": fence}
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise


def get_approval(event: dict[str, Any]) -> dict[str, Any]:
    arn = ((event.get("queryStringParameters") or {}).get("model_package_arn") or "").strip()
    if not arn:
        raise ApiError(400, "model_package_arn query parameter is required")
    pkg = _package(arn)
    meta = pkg.get("CustomerMetadataProperties") or {}
    record = _table("LIFECYCLE_TABLE").get_item(Key=_lifecycle_key(meta)).get("Item") or {}
    return _response(200, {
        "model_package_arn": arn,
        "approval_status": pkg.get("ModelApprovalStatus"),
        "canonical_hash": meta.get("canonical_hash"),
        "lifecycle_state": record.get("state"),
        "evidence_uri": meta.get("evidence_uri"),
    })


def post_decision(event: dict[str, Any]) -> dict[str, Any]:
    caller = _caller(event)
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        raise ApiError(400, "body must be JSON") from exc
    arn = str(body.get("model_package_arn") or "").strip()
    decision = str(body.get("decision") or "").strip().lower()
    request_hash = str(body.get("canonical_hash") or "").strip()
    comment = str(body.get("comment") or "")[:1000]
    if not arn or decision not in DECISIONS or not request_hash:
        raise ApiError(400, "model_package_arn, decision (approve|reject) and canonical_hash are required")

    pkg = _package(arn)
    meta = dict(pkg.get("CustomerMetadataProperties") or {})
    key = _lifecycle_key(meta)
    identity = check_identity(caller["email"], meta["tenant_id"])
    check_separation_of_duties(identity, caller["email"], meta.get("submitted_by", ""))

    fence = acquire_lock(f"approval#{arn}", caller["email"])
    try:
        pkg = _package(arn)
        meta = dict(pkg.get("CustomerMetadataProperties") or {})
        if pkg.get("ModelApprovalStatus") != "PendingManualApproval":
            raise ApiError(409, f"package is {pkg.get('ModelApprovalStatus')}, not PendingManualApproval")
        lifecycle = _table("LIFECYCLE_TABLE")
        record = lifecycle.get_item(Key=key).get("Item") or {}
        if not (request_hash == meta.get("canonical_hash") == record.get("canonical_hash")):
            log_decision(key["pk"], "APPROVAL_HASH_MISMATCH", caller["email"], model_package_arn=arn)
            raise ApiError(409, "canonical hash does not match the registered candidate")

        status = DECISIONS[decision]
        decision_id = log_decision(key["pk"], f"MODEL_{status.upper()}", caller["email"],
                                   model_package_arn=arn, canonical_hash=request_hash, comment=comment,
                                   fence=str(fence))
        decided_by_field = "approved_by" if status == "Approved" else "rejected_by"
        meta.update({"approval_id": decision_id, decided_by_field: caller["email"], "approval_hash": request_hash})
        _sm().update_model_package(
            ModelPackageArn=arn,
            ModelApprovalStatus=status,
            ApprovalDescription=f"{status} via management API by {caller['email']} ({decision_id})"[:1024],
            CustomerMetadataProperties=meta,
        )
        lifecycle.update_item(
            Key=key,
            UpdateExpression="SET #s = :s, approval_id = :d, decided_by = :b, decided_at = :t",
            ConditionExpression="canonical_hash = :h",
            ExpressionAttributeNames={"#s": "state"},
            ExpressionAttributeValues={":s": status.upper(), ":d": decision_id, ":b": caller["email"],
                                       ":t": _now(), ":h": request_hash},
        )
    finally:
        release_lock(f"approval#{arn}", fence)

    return _response(200, {"model_package_arn": arn, "approval_status": status, "approval_id": decision_id})


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = str(event.get("httpMethod") or "").upper()
    try:
        if method == "GET":
            return get_approval(event)
        if method == "POST":
            return post_decision(event)
        return _response(405, {"error": "method not allowed"})
    except ApiError as exc:
        logger.warning("approval_api_refused status=%s reason=%s", exc.status, exc)
        return _response(exc.status, {"error": str(exc)})


handler = lambda_handler

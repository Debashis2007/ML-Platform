"""Unit tests for the management API approval Lambda."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from lambdas.approval_api import handler as mod

ARN = "arn:aws:sagemaker:us-east-1:848973819860:model-package/ModelCreditRisk/1"
META = {"tenant_id": "demo", "model_id": "credit-risk", "model_data_sha256": "a" * 64,
        "canonical_hash": "h1", "submitted_by": "dev1"}
APPROVER = {"pk": "sds@example.com", "roles": ["senior_data_scientist"], "tenants": ["demo"],
            "github_login": "sds-gh", "status": "active"}


@pytest.fixture
def env(monkeypatch):
    for k, v in {"LIFECYCLE_TABLE": "lifecycle", "DECISION_LOG_TABLE": "decision-log",
                 "IDENTITY_TABLE": "identity", "LOCKS_TABLE": "locks"}.items():
        monkeypatch.setenv(k, v)


def _event(email="sds@example.com", decision="approve", chash="h1", method="POST"):
    return {"httpMethod": method, "requestContext": {"authorizer": {"email": email, "principalId": "okta|1"}},
            "body": json.dumps({"model_package_arn": ARN, "decision": decision, "canonical_hash": chash}),
            "queryStringParameters": {"model_package_arn": ARN}}


def _run(event, identity=APPROVER, status="PendingManualApproval", lifecycle_hash="h1", lock_busy=False):
    sm = MagicMock()
    sm.describe_model_package.return_value = {"ModelApprovalStatus": status,
                                              "CustomerMetadataProperties": dict(META)}
    tables = {n: MagicMock() for n in ("lifecycle", "decision-log", "identity", "locks")}
    tables["identity"].get_item.return_value = {"Item": identity} if identity else {}
    tables["lifecycle"].get_item.return_value = {"Item": {"canonical_hash": lifecycle_hash, "state": "PENDING_APPROVAL"}}
    if lock_busy:
        tables["locks"].put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
    names = {"LIFECYCLE_TABLE": "lifecycle", "DECISION_LOG_TABLE": "decision-log",
             "IDENTITY_TABLE": "identity", "LOCKS_TABLE": "locks"}
    with patch.object(mod, "_sm", return_value=sm), \
         patch.object(mod, "_table", side_effect=lambda env_name: tables[names[env_name]]):
        result = mod.lambda_handler(event, SimpleNamespace(aws_request_id="rid"))
    return result, sm, tables


def test_approve_happy_path(env):
    result, sm, tables = _run(_event())
    assert result["statusCode"] == 200
    kwargs = sm.update_model_package.call_args.kwargs
    assert kwargs["ModelApprovalStatus"] == "Approved"
    assert kwargs["CustomerMetadataProperties"]["approval_hash"] == "h1"
    assert kwargs["CustomerMetadataProperties"]["approved_by"] == "sds@example.com"
    tables["locks"].put_item.assert_called_once()
    tables["locks"].delete_item.assert_called_once()
    assert tables["lifecycle"].update_item.call_args.kwargs["ExpressionAttributeValues"][":s"] == "APPROVED"


def test_reject(env):
    result, sm, _ = _run(_event(decision="reject"))
    assert result["statusCode"] == 200
    assert sm.update_model_package.call_args.kwargs["ModelApprovalStatus"] == "Rejected"


@pytest.mark.parametrize("identity", [
    None,
    {**APPROVER, "roles": ["data_scientist"]},
    {**APPROVER, "tenants": ["other"]},
    {**APPROVER, "status": "disabled"},
])
def test_identity_checks(env, identity):
    result, sm, _ = _run(_event(), identity=identity)
    assert result["statusCode"] == 403
    sm.update_model_package.assert_not_called()


def test_separation_of_duties(env):
    result, sm, _ = _run(_event(), identity={**APPROVER, "github_login": "dev1"})
    assert result["statusCode"] == 403 and "separation" in result["body"]
    sm.update_model_package.assert_not_called()


def test_hash_binding(env):
    result, sm, tables = _run(_event(chash="tampered"))
    assert result["statusCode"] == 409
    sm.update_model_package.assert_not_called()
    assert tables["decision-log"].put_item.call_args.kwargs["Item"]["action"] == "APPROVAL_HASH_MISMATCH"
    tables["locks"].delete_item.assert_called_once()


def test_lifecycle_hash_must_agree(env):
    result, sm, _ = _run(_event(), lifecycle_hash="other")
    assert result["statusCode"] == 409
    sm.update_model_package.assert_not_called()


def test_only_pending_packages(env):
    result, sm, _ = _run(_event(), status="Approved")
    assert result["statusCode"] == 409
    sm.update_model_package.assert_not_called()


def test_concurrent_decision_locked(env):
    result, sm, _ = _run(_event(), lock_busy=True)
    assert result["statusCode"] == 409
    sm.update_model_package.assert_not_called()


def test_missing_authorizer_email(env):
    event = _event()
    event["requestContext"] = {}
    result, _, _ = _run(event)
    assert result["statusCode"] == 401


def test_get_returns_hash(env):
    result, _, _ = _run(_event(method="GET"))
    body = json.loads(result["body"])
    assert result["statusCode"] == 200 and body["canonical_hash"] == "h1"

"""Unit tests for capture_approval_event Lambda handler."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from lambdas.capture_approval_event import handler as mod

ARN = "arn:aws:sagemaker:us-east-1:123:model-package/ModelCreditRisk/3"
META = {
    "tenant_id": "demo",
    "model_id": "credit-risk",
    "model_data_sha256": "a" * 64,
    "canonical_hash": "h1",
    "approval_hash": "h1",
    "approval_id": "dec-1",
}


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("DECISION_LOG_TABLE", "decision-log")
    monkeypatch.setenv("LIFECYCLE_TABLE", "lifecycle")
    monkeypatch.setenv("DEPLOY_PARAMETER_PREFIX", "/mlp/deploy")


def _run(event, lifecycle_item):
    tables = {"decision-log": MagicMock(), "lifecycle": MagicMock()}
    tables["lifecycle"].get_item.return_value = {"Item": lifecycle_item} if lifecycle_item else {}
    ddb = MagicMock()
    ddb.Table.side_effect = lambda name: tables[name]
    ssm, events = MagicMock(), MagicMock()
    events.put_events.return_value = {"FailedEntryCount": 0}
    with (
        patch.object(mod, "_ddb", return_value=ddb),
        patch.object(mod, "_ssm", return_value=ssm),
        patch.object(mod, "_events", return_value=events),
    ):
        result = mod.lambda_handler(event, SimpleNamespace(aws_request_id="rid"))
    return result, tables, ssm, events


def _event(status, meta):
    return {"account": "123", "region": "us-east-1", "detail": {
        "ModelPackageGroupName": "ModelCreditRisk", "ModelPackageVersion": "3",
        "ModelPackageArn": ARN, "ModelApprovalStatus": status, "CustomerMetadataProperties": meta}}


def test_api_bound_approval_publishes_deploy_signal(env):
    lifecycle = {"approval_id": "dec-1", "state": "APPROVED", "canonical_hash": "h1"}
    result, tables, ssm, events = _run(_event("Approved", META), lifecycle)
    assert result["statusCode"] == 200
    item = tables["decision-log"].put_item.call_args.kwargs["Item"]
    assert item["action"] == "APPROVAL_CONFIRMED"
    assert ssm.put_parameter.call_count == 2
    assert events.put_events.call_args.kwargs["Entries"][0]["DetailType"] == "Model Approved"


def test_console_approval_is_violation_without_deploy(env):
    meta = {k: v for k, v in META.items() if k not in {"approval_id", "approval_hash"}}
    _, tables, ssm, events = _run(_event("Approved", meta), None)
    assert tables["decision-log"].put_item.call_args.kwargs["Item"]["action"] == "APPROVAL_VIOLATION"
    ssm.put_parameter.assert_not_called()
    assert events.put_events.call_args.kwargs["Entries"][0]["DetailType"] == "Model Approval Violation"


def test_hash_mismatch_is_violation(env):
    lifecycle = {"approval_id": "dec-1", "state": "APPROVED", "canonical_hash": "other"}
    _, tables, ssm, _ = _run(_event("Approved", META), lifecycle)
    assert tables["decision-log"].put_item.call_args.kwargs["Item"]["action"] == "APPROVAL_VIOLATION"
    ssm.put_parameter.assert_not_called()


def test_rejected_skips_deploy_signal(env):
    _, tables, ssm, events = _run(_event("Rejected", META), None)
    assert tables["decision-log"].put_item.call_args.kwargs["Item"]["action"] == "STATE_REJECTED"
    ssm.put_parameter.assert_not_called()
    events.put_events.assert_not_called()

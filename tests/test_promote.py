"""Unit tests for promote_model_package Lambda (record-only promotion by digest)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from lambdas.promote_model_package import handler as mod

DIGEST = "sha256:" + "b" * 64
NONPROD_IMAGE = f"848973819860.dkr.ecr.us-east-1.amazonaws.com/credit-risk@{DIGEST}"
PROD_IMAGE = f"999999999999.dkr.ecr.us-east-1.amazonaws.com/credit-risk@{DIGEST}"
SOURCE_ARN = "arn:aws:sagemaker:us-east-1:848973819860:model-package/ModelCreditRisk/3"


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("TARGET_MODEL_PACKAGE_GROUP", "ModelCreditRisk")
    monkeypatch.setenv("DECISION_LOG_TABLE", "decision-log")
    monkeypatch.delenv("SOURCE_REGISTRY_READ_ROLE_ARN", raising=False)


def _source(status="Approved", approval_id="dec-1", image=NONPROD_IMAGE):
    meta = {"tenant_id": "demo", "model_id": "credit-risk", "source_commit": "abc"}
    if approval_id:
        meta["approval_id"] = approval_id
    return {"ModelApprovalStatus": status, "CustomerMetadataProperties": meta,
            "InferenceSpecification": {"Containers": [{"Image": image, "ModelDataUrl": "s3://b/m.tar.gz"}]}}


def _run(source, ecr_error=None, event=None):
    sm, ecr, events, ddb, table = MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock()
    sm.describe_model_package.return_value = source
    if ecr_error:
        ecr.describe_images.side_effect = ClientError({"Error": {"Code": ecr_error}}, "DescribeImages")
    events.put_events.return_value = {"FailedEntryCount": 0}
    ddb.Table.return_value = table
    with (
        patch.object(mod, "_source_sm", return_value=sm),
        patch.object(mod, "_ecr", return_value=ecr),
        patch.object(mod, "_events", return_value=events),
        patch.object(mod, "_ddb", return_value=ddb),
    ):
        result = mod.lambda_handler(
            event or {"source_model_package_arn": SOURCE_ARN, "prod_image_uri": PROD_IMAGE},
            SimpleNamespace(aws_request_id="rid"),
        )
    return result, sm, table, events


def test_promotion_recorded_without_creating_package(env):
    result, sm, table, events = _run(_source())
    body = json.loads(result["body"])
    assert body["prod_image_uri"] == PROD_IMAGE
    sm.create_model_package.assert_not_called()
    sm.update_model_package.assert_not_called()
    assert table.put_item.call_args.kwargs["Item"]["action"] == "PROMOTION_REQUESTED"
    assert events.put_events.call_args.kwargs["Entries"][0]["DetailType"] == "Model Promotion Requested"


def test_requires_source():
    with pytest.raises(ValueError, match="model_package_arn"):
        mod.lambda_handler({}, SimpleNamespace(aws_request_id="rid"))


def test_requires_digest_uri(env):
    with pytest.raises(ValueError, match="digest"):
        _run(_source(), event={"source_model_package_arn": SOURCE_ARN, "prod_image_uri": "repo:latest"})


def test_refuses_unapproved_source(env):
    with pytest.raises(ValueError, match="not Approved"):
        _run(_source(status="PendingManualApproval"))


def test_refuses_console_approval(env):
    with pytest.raises(ValueError, match="management API"):
        _run(_source(approval_id=None))


def test_refuses_digest_mismatch(env):
    other = NONPROD_IMAGE.replace("b" * 64, "c" * 64)
    with pytest.raises(ValueError, match="differs"):
        _run(_source(image=other))


def test_refuses_digest_missing_in_prod_ecr(env):
    with pytest.raises(ValueError, match="copy it by digest"):
        _run(_source(), ecr_error="ImageNotFoundException")

"""Unit tests for capture_approval_event Lambda handler."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from lambdas.capture_approval_event import handler as mod


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("GOVERNANCE_TABLE", "gov-table")
    monkeypatch.setenv("DEPLOY_PARAMETER_PREFIX", "/mlp/deploy")


def test_approved_writes_ssm_and_event(env):
    table = MagicMock()
    ddb = MagicMock()
    ddb.Table.return_value = table
    ssm = MagicMock()
    events = MagicMock()
    events.put_events.return_value = {"FailedEntryCount": 0}

    event = {
        "account": "123",
        "region": "us-east-1",
        "source": "aws.sagemaker",
        "detail": {
            "ModelPackageGroupName": "ModelCreditRisk",
            "ModelPackageVersion": "3",
            "ModelPackageArn": "arn:aws:sagemaker:us-east-1:123:model-package/ModelCreditRisk/3",
            "ModelApprovalStatus": "Approved",
        },
    }

    with (
        patch.object(mod, "_ddb", return_value=ddb),
        patch.object(mod, "_ssm", return_value=ssm),
        patch.object(mod, "_events", return_value=events),
    ):
        result = mod.lambda_handler(event, SimpleNamespace(aws_request_id="rid"))

    assert result["statusCode"] == 200
    table.put_item.assert_called_once()
    assert ssm.put_parameter.call_count == 2
    events.put_events.assert_called_once()


def test_rejected_skips_deploy_signal(env):
    table = MagicMock()
    ddb = MagicMock()
    ddb.Table.return_value = table
    ssm = MagicMock()
    events = MagicMock()

    event = {
        "detail": {
            "ModelPackageGroupName": "ModelCreditRisk",
            "ModelPackageVersion": "4",
            "ModelPackageArn": "arn:aws:sagemaker:us-east-1:123:model-package/ModelCreditRisk/4",
            "ModelApprovalStatus": "Rejected",
        }
    }

    with (
        patch.object(mod, "_ddb", return_value=ddb),
        patch.object(mod, "_ssm", return_value=ssm),
        patch.object(mod, "_events", return_value=events),
    ):
        mod.handler(event, SimpleNamespace(aws_request_id="rid"))

    table.put_item.assert_called_once()
    ssm.put_parameter.assert_not_called()
    events.put_events.assert_not_called()

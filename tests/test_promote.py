"""Unit tests for promote_model_package Lambda."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from lambdas.promote_model_package import handler as mod


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("TARGET_MODEL_PACKAGE_GROUP", "ModelCreditRisk")
    monkeypatch.setenv("DEPLOY_PARAMETER_PREFIX", "/mlp-hub-prod/deploy")
    monkeypatch.setenv("TARGET_APPROVAL_STATUS", "Approved")


def test_promote_success(env):
    sm = MagicMock()
    sm.describe_model_package.return_value = {
        "InferenceSpecification": {
            "Containers": [{"Image": "123.dkr.ecr.us-east-1.amazonaws.com/x:1", "ModelDataUrl": "s3://b/m.tar.gz"}],
            "SupportedContentTypes": ["application/json"],
            "SupportedResponseMIMETypes": ["application/json"],
        },
        "CustomerMetadataProperties": {"model_name": "credit-risk"},
    }
    sm.create_model_package.return_value = {
        "ModelPackageArn": "arn:aws:sagemaker:us-east-1:999:model-package/ModelCreditRisk/7"
    }
    ssm = MagicMock()
    events = MagicMock()
    events.put_events.return_value = {"FailedEntryCount": 0}

    with (
        patch.object(mod, "_sm", return_value=sm),
        patch.object(mod, "_ssm", return_value=ssm),
        patch.object(mod, "_events", return_value=events),
    ):
        result = mod.lambda_handler(
            {
                "source_model_package_arn": "arn:aws:sagemaker:us-east-1:111:model-package/ModelCreditRisk/3",
                "business_unit": "BU1",
            },
            SimpleNamespace(aws_request_id="rid"),
        )

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["promoted_model_package_arn"].endswith("/7")
    assert body["business_unit"] == "BU1"
    assert ssm.put_parameter.call_count >= 2
    events.put_events.assert_called_once()
    create_kwargs = sm.create_model_package.call_args.kwargs
    assert create_kwargs["ModelLifeCycle"]["Stage"] == "Production"
    assert create_kwargs["ModelLifeCycle"]["StageStatus"] == "Approved"


def test_promote_requires_source(env):
    with pytest.raises(ValueError, match="model_package_arn"):
        mod.lambda_handler({}, SimpleNamespace(aws_request_id="rid"))

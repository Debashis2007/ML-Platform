"""Unit tests for trigger_github_deploy Lambda."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from lambdas.trigger_github_deploy import handler as mod


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("GITHUB_OWNER", "acme")
    monkeypatch.setenv("GITHUB_REPO", "ML-Platform")
    monkeypatch.setenv("GITHUB_TOKEN_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:tok")


def test_dispatch_success(env):
    secrets = MagicMock()
    secrets.get_secret_value.return_value = {"SecretString": "ghp_test_token"}

    class _Resp:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch.object(mod, "_secrets", return_value=secrets), patch(
        "urllib.request.urlopen", return_value=_Resp()
    ) as urlopen:
        result = mod.lambda_handler(
            {
                "detail": {
                    "model_package_arn": "arn:aws:sagemaker:us-east-1:123:model-package/ModelCreditRisk/1",
                    "model_package_group": "ModelCreditRisk",
                    "model_package_version": "1",
                }
            },
            SimpleNamespace(aws_request_id="rid"),
        )

    assert result["statusCode"] == 204
    assert json.loads(result["body"])["dispatched"] is True
    req = urlopen.call_args[0][0]
    assert req.full_url == "https://api.github.com/repos/acme/ML-Platform/dispatches"
    body = json.loads(req.data.decode())
    assert body["event_type"] == "model-approved"
    assert "model_package_arn" in body["client_payload"]


def test_dispatch_http_error(env):
    secrets = MagicMock()
    secrets.get_secret_value.return_value = {"SecretString": json.dumps({"token": "x"})}

    err = HTTPError(
        url="https://api.github.com",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b'{"message":"bad credentials"}'),
    )
    with patch.object(mod, "_secrets", return_value=secrets), patch(
        "urllib.request.urlopen", side_effect=err
    ):
        with pytest.raises(HTTPError):
            mod.lambda_handler(
                {"detail": {"model_package_arn": "arn:aws:sagemaker:us-east-1:123:model-package/x/1"}},
                SimpleNamespace(aws_request_id="rid"),
            )


def test_dispatch_missing_arn(env):
    with pytest.raises(ValueError, match="model_package_arn"):
        mod.lambda_handler({"detail": {}}, SimpleNamespace(aws_request_id="rid"))

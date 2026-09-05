"""Unit tests for invoke_endpoint Lambda handler."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from lambdas.invoke_endpoint import handler as mod


class _Body:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload


@pytest.fixture(autouse=True)
def endpoint_env(monkeypatch):
    monkeypatch.setenv("ENDPOINT_NAME", "credit-risk")
    monkeypatch.setenv("MODEL_VERSION", "v1")


def test_handler_success():
    mock_client = MagicMock()
    mock_client.invoke_endpoint.return_value = {
        "Body": _Body({"prediction": [1], "score": [0.9]})
    }
    with patch.object(mod, "_runtime", return_value=mock_client):
        result = mod.handler(
            {"body": json.dumps({"features": [0.1, 0.2]})},
            SimpleNamespace(aws_request_id="req-1"),
        )
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["prediction"] == [1]
    assert body["score"] == [0.9]
    assert body["request_id"] == "req-1"
    mock_client.invoke_endpoint.assert_called_once()


def test_handler_bad_json():
    result = mod.handler({"body": "{not-json"}, SimpleNamespace(aws_request_id="req-2"))
    assert result["statusCode"] == 400
    assert json.loads(result["body"])["error"] == "bad_request"


def test_handler_missing_endpoint(monkeypatch):
    monkeypatch.delenv("ENDPOINT_NAME", raising=False)
    result = mod.handler({"body": "{}"}, SimpleNamespace(aws_request_id="req-3"))
    assert result["statusCode"] == 500
    assert json.loads(result["body"])["error"] == "server_misconfigured"

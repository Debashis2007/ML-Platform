"""Unit tests for the Okta TOKEN authorizer."""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

jwt = pytest.importorskip("jwt")
from cryptography.hazmat.primitives.asymmetric import rsa  # noqa: E402

from lambdas.okta_authorizer import handler as mod  # noqa: E402

ISSUER = "https://example.okta.com/oauth2/default"
AUDIENCE = "api://ml-platform"
METHOD_ARN = "arn:aws:execute-api:us-east-1:848973819860:abc123/prod/POST/approvals"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("OKTA_ISSUER", ISSUER)
    monkeypatch.setenv("OKTA_AUDIENCE", AUDIENCE)
    monkeypatch.setenv("REQUIRED_SCOPE", "ml.approve")


def _token(**overrides):
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": "00u1", "iat": now, "exp": now + 300,
              "email": "SDS@example.com", "scp": ["ml.approve"], "groups": ["ml-sds"]}
    claims.update(overrides)
    return jwt.encode(claims, KEY, algorithm="RS256")


def _call(token):
    jwks = SimpleNamespace(get_signing_key_from_jwt=lambda _t: SimpleNamespace(key=KEY.public_key()))
    with patch.object(mod, "_jwks", return_value=jwks):
        return mod.lambda_handler({"authorizationToken": f"Bearer {token}", "methodArn": METHOD_ARN}, None)


def test_valid_token_allows_with_context():
    result = _call(_token())
    statement = result["policyDocument"]["Statement"][0]
    assert statement["Effect"] == "Allow"
    assert statement["Resource"] == "arn:aws:execute-api:us-east-1:848973819860:abc123/prod/*"
    assert result["context"]["email"] == "sds@example.com"


@pytest.mark.parametrize("overrides", [
    {"aud": "other"},
    {"iss": "https://evil.example.com"},
    {"exp": int(time.time()) - 10},
    {"scp": ["read"]},
])
def test_invalid_tokens_unauthorized(overrides):
    with pytest.raises(Exception, match="Unauthorized"):
        _call(_token(**overrides))


def test_missing_bearer_unauthorized():
    with pytest.raises(Exception, match="Unauthorized"):
        mod.lambda_handler({"authorizationToken": "", "methodArn": METHOD_ARN}, None)

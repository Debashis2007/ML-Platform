"""API Gateway TOKEN authorizer validating Okta-issued JWTs (no Cognito).

Env:
  OKTA_ISSUER      e.g. https://example.okta.com/oauth2/<server-id>
  OKTA_AUDIENCE    expected aud claim
  REQUIRED_SCOPE   optional scope the token must carry (e.g. ml.approve)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import jwt

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_JWKS: jwt.PyJWKClient | None = None


def _jwks() -> jwt.PyJWKClient:
    global _JWKS
    if _JWKS is None:
        _JWKS = jwt.PyJWKClient(f"{os.environ['OKTA_ISSUER'].rstrip('/')}/v1/keys", cache_keys=True)
    return _JWKS


def _api_arn_wildcard(method_arn: str) -> str:
    # arn:aws:execute-api:region:account:api-id/stage/METHOD/path -> .../stage/*
    head, _, rest = method_arn.partition("/")
    stage = rest.split("/", 1)[0] if rest else "*"
    return f"{head}/{stage}/*"


def _policy(principal: str, effect: str, resource: str, context: dict[str, str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "principalId": principal,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}],
        },
    }
    if context:
        result["context"] = context
    return result


def validate(token: str) -> dict[str, Any]:
    signing_key = _jwks().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=os.environ["OKTA_AUDIENCE"],
        issuer=os.environ["OKTA_ISSUER"].rstrip("/"),
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )
    required = os.environ.get("REQUIRED_SCOPE", "").strip()
    if required:
        scopes = claims.get("scp") or str(claims.get("scope", "")).split()
        if required not in scopes:
            raise jwt.InvalidTokenError(f"missing scope {required}")
    return claims


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    raw = str(event.get("authorizationToken") or "")
    token = raw[7:].strip() if raw.lower().startswith("bearer ") else ""
    if not token:
        raise Exception("Unauthorized")  # API Gateway maps this exact message to 401
    try:
        claims = validate(token)
    except jwt.PyJWTError as exc:
        logger.warning("token_rejected reason=%s", exc)
        raise Exception("Unauthorized") from exc

    email = str(claims.get("email") or claims.get("sub") or "").lower()
    groups = claims.get("groups") or []
    return _policy(
        str(claims["sub"]),
        "Allow",
        _api_arn_wildcard(str(event.get("methodArn", ""))),
        {"email": email, "sub": str(claims["sub"]), "groups": ",".join(map(str, groups))[:1000]},
    )


handler = lambda_handler

"""Trigger GitHub repository_dispatch when a model is approved."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

import boto3
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_CONFIG = Config(retries={"max_attempts": 5, "mode": "adaptive"})
_SECRETS = None


def _secrets():
    global _SECRETS
    if _SECRETS is None:
        _SECRETS = boto3.client("secretsmanager", config=_CONFIG)
    return _SECRETS


def _token() -> str:
    secret_arn = os.environ["GITHUB_TOKEN_SECRET_ARN"]
    resp = _secrets().get_secret_value(SecretId=secret_arn)
    raw = resp.get("SecretString") or ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return str(parsed.get("token") or parsed.get("github_token") or next(iter(parsed.values())))
    except json.JSONDecodeError:
        pass
    return raw.strip()


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    owner = os.environ["GITHUB_OWNER"]
    repo = os.environ["GITHUB_REPO"]
    detail = event.get("detail") or event
    if isinstance(detail, str):
        detail = json.loads(detail)

    package_arn = detail.get("model_package_arn") or detail.get("ModelPackageArn")
    group = detail.get("model_package_group") or detail.get("ModelPackageGroupName")
    version = detail.get("model_package_version") or detail.get("ModelPackageVersion")
    if not package_arn:
        raise ValueError("model_package_arn missing from event detail")

    payload = {
        "event_type": "model-approved",
        "client_payload": {
            "model_package_arn": package_arn,
            "model_package_group": group,
            "model_package_version": version,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=f"https://api.github.com/repos/{owner}/{repo}/dispatches",
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
            "User-Agent": "ml-platform-governance",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = getattr(resp, "status", 204)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        logger.error("GitHub dispatch failed status=%s body=%s", exc.code, err_body)
        raise

    logger.info(
        "github_dispatch_sent owner=%s repo=%s status=%s arn=%s",
        owner,
        repo,
        status,
        package_arn,
    )
    return {"statusCode": status, "body": json.dumps({"dispatched": True, "model_package_arn": package_arn})}


handler = lambda_handler

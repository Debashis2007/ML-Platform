"""API Gateway → SageMaker endpoint invoke Lambda."""

from __future__ import annotations

import json
import logging
import os
import traceback
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_RETRY = Config(retries={"max_attempts": 5, "mode": "adaptive"})
_RUNTIME = None
_MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", "1048576"))  # 1 MiB


def _runtime():
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = boto3.client("sagemaker-runtime", config=_RETRY)
    return _RUNTIME


def _response(status: int, body: dict[str, Any], *, request_id: str | None = None) -> dict[str, Any]:
    payload = dict(body)
    if request_id:
        payload.setdefault("request_id", request_id)
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
        "body": json.dumps(payload, default=str),
    }


def _parse_body(event: dict[str, Any]) -> Any:
    body = event.get("body")
    if body is None:
        if "features" in event:
            return event["features"] if not isinstance(event.get("features"), dict) else event
        return event
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    if isinstance(body, str):
        if len(body.encode("utf-8")) > _MAX_BODY_BYTES:
            raise ValueError("Request body exceeds size limit")
        body = body.strip()
        if not body:
            raise ValueError("Request body is empty")
        return json.loads(body)
    return body


def _normalize_payload(parsed: Any) -> str:
    if isinstance(parsed, dict) and "features" in parsed and len(parsed) == 1:
        payload = parsed["features"]
    else:
        payload = parsed
    encoded = json.dumps(payload)
    if len(encoded.encode("utf-8")) > _MAX_BODY_BYTES:
        raise ValueError("Request body exceeds size limit")
    return encoded


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    request_id = getattr(context, "aws_request_id", None)
    endpoint = os.environ.get("ENDPOINT_NAME")
    if not endpoint:
        logger.error("ENDPOINT_NAME is not set")
        return _response(500, {"error": "server_misconfigured"}, request_id=request_id)

    try:
        parsed = _parse_body(event or {})
        payload = _normalize_payload(parsed)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Bad request request_id=%s error=%s", request_id, exc)
        return _response(400, {"error": "bad_request", "message": str(exc)}, request_id=request_id)

    try:
        response = _runtime().invoke_endpoint(
            EndpointName=endpoint,
            ContentType="application/json",
            Accept="application/json",
            Body=payload,
        )
        raw = response["Body"].read().decode("utf-8")
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {"prediction": raw}

        if isinstance(result, dict):
            body = {
                "prediction": result.get("prediction", result.get("predictions", result)),
                "score": result.get("score"),
                "model_version": result.get("model_version") or os.environ.get("MODEL_VERSION"),
                "endpoint": endpoint,
            }
        else:
            body = {
                "prediction": result,
                "score": None,
                "model_version": os.environ.get("MODEL_VERSION"),
                "endpoint": endpoint,
            }
        return _response(200, body, request_id=request_id)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        logger.error("SageMaker invoke failed request_id=%s code=%s error=%s", request_id, code, exc)
        if code in {"ValidationError", "ModelError"}:
            return _response(400, {"error": "inference_error", "message": str(exc)}, request_id=request_id)
        return _response(502, {"error": "upstream_error", "message": code or "invoke_failed"}, request_id=request_id)
    except Exception as exc:  # noqa: BLE001 — map unexpected failures to 500
        logger.error("Unhandled invoke error request_id=%s\n%s", request_id, traceback.format_exc())
        return _response(500, {"error": "internal_error", "message": str(exc)}, request_id=request_id)

"""Copy-in registration: trusted control-plane Lambda that registers a passing candidate.

Trigger: EventBridge "SageMaker Model Building Pipeline Execution Status Change" with
status Succeeded, from the control plane (POC training) or forwarded from a BU account.

The Lambda copies the artefact and evidence into control-plane Object Lock buckets with
SHA-256 verification, then creates a PendingManualApproval package. Its role must be
denied sagemaker:UpdateModelPackage so it can never approve.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_CONFIG = Config(retries={"max_attempts": 8, "mode": "adaptive"})
_CLIENTS: dict[str, Any] = {}

PENDING = "PendingManualApproval"
CANONICAL_FIELDS = (
    "tenant_id",
    "model_id",
    "model_package_group",
    "model_data_sha256",
    "image_uri",
    "source_commit",
    "metrics",
)


class CandidateRejected(Exception):
    """The candidate failed verification; recorded in the decision log."""


def _client(name: str) -> Any:
    if name not in _CLIENTS:
        _CLIENTS[name] = boto3.client(name, config=_CONFIG)
    return _CLIENTS[name]


def _table(name: str) -> Any:
    if "ddb" not in _CLIENTS:
        _CLIENTS["ddb"] = boto3.resource("dynamodb", config=_CONFIG)
    return _CLIENTS["ddb"].Table(name)


def _source_clients(account: str) -> tuple[Any, Any]:
    """SageMaker and S3 clients for the training account (assume role when it is not ours)."""
    role_name = os.environ.get("SOURCE_READ_ROLE_NAME", "")
    own = os.environ.get("CONTROL_PLANE_ACCOUNT_ID", "")
    if not role_name or account == own:
        return _client("sagemaker"), _client("s3")
    creds = _client("sts").assume_role(
        RoleArn=f"arn:aws:iam::{account}:role/{role_name}",
        RoleSessionName="ml-register-candidate",
        DurationSeconds=900,
    )["Credentials"]
    session = boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )
    return session.client("sagemaker", config=_CONFIG), session.client("s3", config=_CONFIG)


def canonical_hash(candidate: dict[str, Any]) -> str:
    """Hash binding the approval to exactly what was evaluated and copied in."""
    payload = {k: candidate.get(k) for k in CANONICAL_FIELDS}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _split_s3(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise CandidateRejected(f"not an s3 URI: {uri!r}")
    return parsed.netloc, parsed.path.lstrip("/")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_decision(model_key: str, action: str, **fields: Any) -> None:
    item = {"pk": model_key, "sk": f"{_now()}#{uuid.uuid4().hex}", "action": action, "actor": "register_candidate"}
    item.update({k: (json.dumps(v, default=str) if isinstance(v, (dict, list)) else v)
                 for k, v in fields.items() if v is not None})
    _table(os.environ["DECISION_LOG_TABLE"]).put_item(Item=item)


def _pipeline_parameters(sm: Any, execution_arn: str) -> dict[str, str]:
    params: dict[str, str] = {}
    kwargs: dict[str, Any] = {"PipelineExecutionArn": execution_arn}
    while True:
        page = sm.list_pipeline_parameters_for_execution(**kwargs)
        params.update({p["Name"]: p["Value"] for p in page.get("PipelineParameters", [])})
        if not page.get("NextToken"):
            return params
        kwargs["NextToken"] = page["NextToken"]


def _load_candidate(s3: Any, output_prefix: str) -> dict[str, Any] | None:
    bucket, prefix = _split_s3(output_prefix.rstrip("/"))
    try:
        body = s3.get_object(Bucket=bucket, Key=f"{prefix}/candidate/candidate.json")["Body"].read()
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
            return None
        raise
    return json.loads(body)


def verify_candidate(candidate: dict[str, Any], params: dict[str, str], source_account: str) -> None:
    image = str(candidate.get("image_uri", ""))
    if "@sha256:" not in image:
        raise CandidateRejected("image_uri is not pinned by digest")
    if image != params.get("ImageUri"):
        raise CandidateRejected("candidate image_uri does not match the pipeline ImageUri parameter")
    if candidate.get("source_commit") != params.get("SourceCommit"):
        raise CandidateRejected("candidate source_commit does not match the pipeline SourceCommit parameter")
    if str(candidate.get("source_account_id")) != source_account:
        raise CandidateRejected("candidate source_account_id does not match the event account")
    sha = str(candidate.get("model_data_sha256", ""))
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise CandidateRejected("model_data_sha256 is not a hex SHA-256")
    prefix = params.get("OutputPrefix", "").rstrip("/") + "/"
    if not str(candidate.get("model_data_url", "")).startswith(prefix):
        raise CandidateRejected("model_data_url is outside this execution's OutputPrefix")
    metrics = candidate.get("metrics") or {}
    for metric, minimum in (candidate.get("thresholds") or {}).items():
        if float(metrics.get(metric, float("-inf"))) < float(minimum):
            raise CandidateRejected(f"threshold not met for {metric}")
    if not candidate.get("thresholds"):
        raise CandidateRejected("candidate carries no thresholds")


def copy_with_checksum(s3: Any, source_uri: str, dest_bucket: str, dest_key: str, expected_hex: str) -> str:
    """Server-side copy with SHA-256 and verify it equals the checksum the pipeline computed."""
    src_bucket, src_key = _split_s3(source_uri)
    expected_b64 = base64.b64encode(bytes.fromhex(expected_hex)).decode("ascii")
    s3.copy_object(
        Bucket=dest_bucket,
        Key=dest_key,
        CopySource={"Bucket": src_bucket, "Key": src_key},
        ChecksumAlgorithm="SHA256",
        MetadataDirective="REPLACE",
        Metadata={"sha256": expected_hex},
    )
    head = s3.head_object(Bucket=dest_bucket, Key=dest_key, ChecksumMode="ENABLED")
    actual = head.get("ChecksumSHA256", "")
    if actual != expected_b64:
        raise CandidateRejected(f"checksum mismatch for s3://{dest_bucket}/{dest_key}")
    return f"s3://{dest_bucket}/{dest_key}"


def _put_evidence(s3: Any, bucket: str, key: str, body: bytes) -> str:
    s3.put_object(Bucket=bucket, Key=key, Body=body, ChecksumAlgorithm="SHA256",
                  ContentType="application/json")
    return f"s3://{bucket}/{key}"


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    detail = event.get("detail") or {}
    status = detail.get("currentPipelineExecutionStatus")
    execution_arn = detail.get("pipelineExecutionArn", "")
    if status != "Succeeded" or not execution_arn:
        return {"statusCode": 204, "body": "ignored"}

    source_account = str(event.get("account") or execution_arn.split(":")[4])
    allowed = {a.strip() for a in os.environ.get("ALLOWED_SOURCE_ACCOUNTS", "").split(",") if a.strip()}
    if allowed and source_account not in allowed:
        logger.warning("rejected_source_account account=%s execution=%s", source_account, execution_arn)
        return {"statusCode": 403, "body": "source account not allowed"}

    src_sm, src_s3 = _source_clients(source_account)
    params = _pipeline_parameters(src_sm, execution_arn)
    output_prefix = params.get("OutputPrefix", "")
    if not output_prefix:
        raise ValueError(f"OutputPrefix parameter missing for {execution_arn}")

    candidate = _load_candidate(src_s3, output_prefix)
    if candidate is None:
        logger.info("no_candidate execution=%s (evaluation gate not met)", execution_arn)
        return {"statusCode": 204, "body": "no candidate"}

    model_key = f"{candidate.get('tenant_id')}#{candidate.get('model_id')}"
    try:
        verify_candidate(candidate, params, source_account)
    except CandidateRejected as exc:
        log_decision(model_key, "CANDIDATE_REJECTED", reason=str(exc), pipeline_execution_arn=execution_arn)
        logger.error("candidate_rejected execution=%s reason=%s", execution_arn, exc)
        return {"statusCode": 422, "body": str(exc)}

    sha = candidate["model_data_sha256"]
    lifecycle = _table(os.environ["LIFECYCLE_TABLE"])
    lifecycle_key = {"pk": model_key, "sk": f"PKG#{sha}"}
    existing = lifecycle.get_item(Key=lifecycle_key).get("Item")
    if existing and existing.get("model_package_arn"):
        return {"statusCode": 200, "body": json.dumps({"model_package_arn": existing["model_package_arn"],
                                                       "idempotent": True})}

    chash = canonical_hash(candidate)
    if not existing:
        try:
            lifecycle.put_item(
                Item={**lifecycle_key, "state": "COPY_IN_STARTED", "canonical_hash": chash,
                      "pipeline_execution_arn": execution_arn, "source_account_id": source_account,
                      "created_at": _now()},
                ConditionExpression="attribute_not_exists(pk)",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise

    base = f"{candidate['tenant_id']}/{candidate['model_id']}/{sha}"
    dest_s3 = _client("s3")
    try:
        artefact_uri = copy_with_checksum(
            dest_s3, candidate["model_data_url"], os.environ["ARTEFACT_BUCKET"], f"{base}/model.tar.gz", sha
        )
    except CandidateRejected as exc:
        log_decision(model_key, "CANDIDATE_REJECTED", reason=str(exc), pipeline_execution_arn=execution_arn)
        lifecycle.update_item(Key=lifecycle_key, UpdateExpression="SET #s = :s",
                              ExpressionAttributeNames={"#s": "state"},
                              ExpressionAttributeValues={":s": "COPY_IN_FAILED"})
        raise

    evidence_bucket = os.environ["EVIDENCE_BUCKET"]
    candidate_uri = _put_evidence(dest_s3, evidence_bucket, f"{base}/candidate.json",
                                  json.dumps(candidate, sort_keys=True).encode("utf-8"))
    metrics_uri = _put_evidence(dest_s3, evidence_bucket, f"{base}/metrics.json",
                                json.dumps(candidate.get("metrics") or {}, sort_keys=True).encode("utf-8"))

    metadata = {
        "tenant_id": candidate["tenant_id"],
        "model_id": candidate["model_id"],
        "platform_version": str(candidate.get("platform_version", "")),
        "canonical_hash": chash,
        "model_data_sha256": sha,
        "source_commit": str(candidate.get("source_commit", "")),
        "source_account_id": source_account,
        "pipeline_execution_arn": execution_arn[:1024],
        "evidence_uri": candidate_uri[:1024],
        "submitted_by": str(params.get("SubmittedBy", ""))[:256],
    }
    if candidate.get("lineage_source_package_arn"):
        metadata["lineage_source_package_arn"] = str(candidate["lineage_source_package_arn"])[:1024]

    response = _client("sagemaker").create_model_package(
        ModelPackageGroupName=candidate["model_package_group"],
        ModelPackageDescription=f"{candidate['model_id']} {sha[:12]} commit {str(candidate.get('source_commit', ''))[:12]}",
        ModelApprovalStatus=PENDING,
        ClientToken=chash[:36],
        InferenceSpecification={
            "Containers": [{"Image": candidate["image_uri"], "ModelDataUrl": artefact_uri}],
            "SupportedContentTypes": ["application/json", "text/csv"],
            "SupportedResponseMIMETypes": ["application/json"],
        },
        ModelMetrics={"ModelQuality": {"Statistics": {"ContentType": "application/json", "S3Uri": metrics_uri}}},
        CustomerMetadataProperties=metadata,
    )
    package_arn = response["ModelPackageArn"]

    lifecycle.update_item(
        Key=lifecycle_key,
        UpdateExpression="SET #s = :s, model_package_arn = :a, artefact_uri = :u, evidence_uri = :e, "
                         "image_uri = :i, submitted_by = :b, updated_at = :t",
        ExpressionAttributeNames={"#s": "state"},
        ExpressionAttributeValues={":s": "PENDING_APPROVAL", ":a": package_arn, ":u": artefact_uri,
                                   ":e": candidate_uri, ":i": candidate["image_uri"],
                                   ":b": metadata["submitted_by"], ":t": _now()},
    )
    log_decision(model_key, "CANDIDATE_REGISTERED", model_package_arn=package_arn, canonical_hash=chash,
                 pipeline_execution_arn=execution_arn, artefact_uri=artefact_uri)
    logger.info("candidate_registered package=%s hash=%s", package_arn, chash)
    return {"statusCode": 200, "body": json.dumps({"model_package_arn": package_arn, "canonical_hash": chash})}


handler = lambda_handler

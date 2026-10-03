"""Unit tests for the copy-in registration Lambda."""

from __future__ import annotations

import base64
import io
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from lambdas.register_candidate import handler as mod

ACCOUNT = "848973819860"
EXEC_ARN = f"arn:aws:sagemaker:us-east-1:{ACCOUNT}:pipeline/demo-credit-risk/execution/abc123"
SHA = "d" * 64
IMAGE = f"{ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/credit-risk@sha256:" + "e" * 64
PREFIX = "s3://run-bucket/pipelines/credit-risk/run1"
PARAMS = {"ImageUri": IMAGE, "OutputPrefix": PREFIX, "SourceCommit": "c0ffee", "SubmittedBy": "dev1",
          "DataUri": "s3://data/x", "LineageSourcePackageArn": ""}


def _candidate(**overrides):
    candidate = {
        "tenant_id": "demo", "model_id": "credit-risk", "model_package_group": "ModelCreditRisk",
        "platform_version": "v1.0.0", "source_account_id": ACCOUNT, "source_commit": "c0ffee",
        "image_uri": IMAGE, "model_data_url": f"{PREFIX}/model/job/output/model.tar.gz",
        "model_data_sha256": SHA, "metrics": {"auc": 0.81}, "thresholds": {"auc": 0.75},
    }
    candidate.update(overrides)
    return candidate


@pytest.fixture
def env(monkeypatch):
    for k, v in {"LIFECYCLE_TABLE": "lifecycle", "DECISION_LOG_TABLE": "decision-log",
                 "ARTEFACT_BUCKET": "artefacts", "EVIDENCE_BUCKET": "evidence",
                 "ALLOWED_SOURCE_ACCOUNTS": ACCOUNT, "CONTROL_PLANE_ACCOUNT_ID": ACCOUNT}.items():
        monkeypatch.setenv(k, v)


def _event(status="Succeeded", account=ACCOUNT):
    return {"account": account, "detail": {"currentPipelineExecutionStatus": status,
                                           "pipelineExecutionArn": EXEC_ARN}}


def _run(candidate, lifecycle_item=None, checksum_hex=SHA, event=None):
    sm = MagicMock()
    sm.list_pipeline_parameters_for_execution.return_value = {
        "PipelineParameters": [{"Name": k, "Value": v} for k, v in PARAMS.items()]}
    sm.create_model_package.return_value = {"ModelPackageArn": "arn:pkg/ModelCreditRisk/1"}
    s3 = MagicMock()
    if candidate is None:
        s3.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    else:
        s3.get_object.return_value = {"Body": io.BytesIO(json.dumps(candidate).encode())}
    s3.head_object.return_value = {"ChecksumSHA256": base64.b64encode(bytes.fromhex(checksum_hex)).decode()}
    tables = {"lifecycle": MagicMock(), "decision-log": MagicMock()}
    tables["lifecycle"].get_item.return_value = {"Item": lifecycle_item} if lifecycle_item else {}
    clients = {"sagemaker": sm, "s3": s3}
    with (
        patch.object(mod, "_source_clients", return_value=(sm, s3)),
        patch.object(mod, "_client", side_effect=lambda n: clients[n]),
        patch.object(mod, "_table", side_effect=lambda n: tables[n]),
    ):
        result = mod.lambda_handler(event or _event(), SimpleNamespace(aws_request_id="rid"))
    return result, sm, s3, tables


def _actions(tables):
    return [c.kwargs["Item"]["action"] for c in tables["decision-log"].put_item.call_args_list]


def test_registers_pending_package_with_checksum_copy(env):
    result, sm, s3, tables = _run(_candidate())
    assert result["statusCode"] == 200
    kwargs = sm.create_model_package.call_args.kwargs
    assert kwargs["ModelApprovalStatus"] == "PendingManualApproval"
    container = kwargs["InferenceSpecification"]["Containers"][0]
    assert container["Image"] == IMAGE
    assert container["ModelDataUrl"] == f"s3://artefacts/demo/credit-risk/{SHA}/model.tar.gz"
    meta = kwargs["CustomerMetadataProperties"]
    assert meta["canonical_hash"] == mod.canonical_hash(_candidate())
    assert meta["submitted_by"] == "dev1"
    assert s3.copy_object.call_args.kwargs["ChecksumAlgorithm"] == "SHA256"
    sm.update_model_package.assert_not_called()
    assert _actions(tables) == ["CANDIDATE_REGISTERED"]


def test_ignores_non_succeeded(env):
    result, sm, _, _ = _run(_candidate(), event=_event(status="Failed"))
    assert result["statusCode"] == 204
    sm.create_model_package.assert_not_called()


def test_rejects_unknown_account(env):
    result, sm, _, _ = _run(_candidate(), event=_event(account="111111111111"))
    assert result["statusCode"] == 403
    sm.create_model_package.assert_not_called()


def test_no_candidate_means_gate_not_met(env):
    result, sm, _, _ = _run(None)
    assert result["statusCode"] == 204
    sm.create_model_package.assert_not_called()


@pytest.mark.parametrize("overrides,reason", [
    ({"image_uri": "repo:latest"}, "digest"),
    ({"source_commit": "other"}, "SourceCommit"),
    ({"model_data_url": "s3://elsewhere/model.tar.gz"}, "OutputPrefix"),
    ({"metrics": {"auc": 0.5}}, "threshold"),
])
def test_rejects_tampered_candidate(env, overrides, reason):
    result, sm, _, tables = _run(_candidate(**overrides))
    assert result["statusCode"] == 422 and reason in result["body"]
    sm.create_model_package.assert_not_called()
    assert _actions(tables) == ["CANDIDATE_REJECTED"]


def test_checksum_mismatch_blocks_registration(env):
    with pytest.raises(mod.CandidateRejected, match="checksum"):
        _run(_candidate(), checksum_hex="f" * 64)


def test_idempotent_when_already_registered(env):
    result, sm, s3, _ = _run(_candidate(), lifecycle_item={"model_package_arn": "arn:existing"})
    assert json.loads(result["body"]) == {"model_package_arn": "arn:existing", "idempotent": True}
    sm.create_model_package.assert_not_called()
    s3.copy_object.assert_not_called()


def test_canonical_hash_matches_approval_inputs():
    a = mod.canonical_hash(_candidate())
    assert a == mod.canonical_hash(_candidate(created_at="later", thresholds={"auc": 0.1}))
    assert a != mod.canonical_hash(_candidate(model_data_sha256="0" * 64))

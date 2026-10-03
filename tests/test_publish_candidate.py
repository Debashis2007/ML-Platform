"""Tests for the platform PublishCandidate script."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from ml_platform.scripts import publish_candidate as mod

IMAGE = "123456789012.dkr.ecr.us-east-1.amazonaws.com/credit-risk@sha256:" + "e" * 64


def _setup(tmp_path: Path, auc: float):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    (model_dir / "model.tar.gz").write_bytes(b"artefact-bytes")
    eval_dir = tmp_path / "evaluation"
    eval_dir.mkdir()
    (eval_dir / "metrics.json").write_text(json.dumps({"auc": auc}), encoding="utf-8")
    return model_dir, eval_dir


def _argv(tmp_path, model_dir, eval_dir, image=IMAGE):
    return ["publish_candidate.py", "--model-dir", str(model_dir), "--evaluation-dir", str(eval_dir),
            "--output-dir", str(tmp_path / "out"), "--model-data-url", "s3://b/run/model/model.tar.gz",
            "--image-uri", image, "--source-commit", "abc", "--tenant-id", "demo", "--model-id", "credit-risk",
            "--model-package-group", "ModelCreditRisk", "--platform-version", "v1.0.0",
            "--source-account-id", "123456789012", "--thresholds", json.dumps({"auc": 0.75})]


def test_writes_manifest_with_sha256(tmp_path, monkeypatch):
    model_dir, eval_dir = _setup(tmp_path, 0.8)
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, model_dir, eval_dir))
    mod.main()
    manifest = json.loads((tmp_path / "out" / "candidate.json").read_text(encoding="utf-8"))
    assert manifest["model_data_sha256"] == hashlib.sha256(b"artefact-bytes").hexdigest()
    assert manifest["image_uri"] == IMAGE
    assert manifest["metrics"]["auc"] == 0.8
    assert manifest["lineage_source_package_arn"] is None


def test_refuses_below_threshold(tmp_path, monkeypatch):
    model_dir, eval_dir = _setup(tmp_path, 0.5)
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, model_dir, eval_dir))
    with pytest.raises(ValueError, match="Thresholds"):
        mod.main()


def test_refuses_tag_image(tmp_path, monkeypatch):
    model_dir, eval_dir = _setup(tmp_path, 0.8)
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, model_dir, eval_dir, image="repo:latest"))
    with pytest.raises(ValueError, match="digest"):
        mod.main()

"""Tests for model source resolution helpers."""

from __future__ import annotations

import pytest

from ml_platform.steps.common import model_source_dir, script_path


def test_model_source_dir_credit_risk():
    path = model_source_dir("credit-risk")
    assert (path / "train.py").is_file()
    assert script_path("credit-risk", "evaluate.py").endswith("evaluate.py")


def test_model_repo_cwd_wins_over_bundled_example(tmp_path, monkeypatch):
    (tmp_path / "train.py").write_text("# model repo train\n", encoding="utf-8")
    (tmp_path / "model.yaml").write_text("model:\n  id: credit-risk\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert model_source_dir("credit-risk") == tmp_path


def test_cwd_with_other_model_id_is_skipped(tmp_path, monkeypatch):
    (tmp_path / "train.py").write_text("# other\n", encoding="utf-8")
    (tmp_path / "model.yaml").write_text("model:\n  id: fraud\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert model_source_dir("credit-risk") != tmp_path


def test_model_source_dir_missing():
    with pytest.raises(FileNotFoundError, match="No model source directory"):
        model_source_dir("does-not-exist-model-xyz")

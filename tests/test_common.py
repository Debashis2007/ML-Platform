"""Tests for model source resolution helpers."""

from __future__ import annotations

import pytest

from ml_platform.steps.common import model_source_dir, script_path


def test_model_source_dir_credit_risk():
    path = model_source_dir("credit-risk")
    assert (path / "train.py").is_file()
    assert script_path("credit-risk", "evaluate.py").endswith("evaluate.py")


def test_model_source_dir_missing():
    with pytest.raises(FileNotFoundError, match="No model source directory"):
        model_source_dir("does-not-exist-model-xyz")

"""Smoke tests for OOTB JumpStart register helper (no AWS)."""

from __future__ import annotations

from examples.ootb_jumpstart import register_ootb as mod


def test_default_model_id():
    assert mod.DEFAULT_MODEL_ID == "xgboost-classification-model"

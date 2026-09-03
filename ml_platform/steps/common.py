"""Shared helpers for SageMaker pipeline step modules."""

from __future__ import annotations

from pathlib import Path


def model_source_dir(model_name: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    slug = model_name.replace("_", "-")
    candidate = root / "examples" / slug
    if candidate.exists():
        return candidate
    return root / "examples" / "credit-risk"


def script_path(model_name: str, filename: str) -> str:
    return str(model_source_dir(model_name) / filename)

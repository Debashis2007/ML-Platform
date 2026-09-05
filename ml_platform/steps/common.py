"""Shared helpers for SageMaker pipeline step modules."""

from __future__ import annotations

from pathlib import Path


def model_source_dir(model_name: str) -> Path:
    """Resolve the model project directory; never silently fall back to another model."""
    root = Path(__file__).resolve().parents[2]
    slug = model_name.replace("_", "-")
    candidates = [
        root / "examples" / slug,
        Path.cwd() / "examples" / slug,
        Path.cwd(),
    ]
    for candidate in candidates:
        train = candidate / "train.py"
        if not train.is_file():
            continue
        # When resolving CWD, require pipeline.yaml model name to match when present.
        pipeline_yaml = candidate / "pipeline.yaml"
        if candidate == Path.cwd() and pipeline_yaml.is_file():
            try:
                import yaml

                data = yaml.safe_load(pipeline_yaml.read_text(encoding="utf-8")) or {}
                if str(data.get("model", "")).replace("_", "-") not in {slug, model_name}:
                    continue
            except Exception:
                continue
        return candidate

    searched = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        f"No model source directory for {model_name!r} containing train.py. Searched: {searched}"
    )


def script_path(model_name: str, filename: str) -> str:
    path = model_source_dir(model_name) / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required script missing: {path}")
    return str(path)

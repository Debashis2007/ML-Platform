"""Shared helpers for SageMaker pipeline step modules."""

from __future__ import annotations

from pathlib import Path


def model_source_dir(model_id: str) -> Path:
    """Resolve the model project directory; never silently fall back to another model."""
    root = Path(__file__).resolve().parents[2]
    slug = model_id.replace("_", "-")
    # A model repo running from its own root must win over the platform's bundled examples.
    candidates = [
        Path.cwd(),
        root / "examples" / slug,
        Path.cwd() / "examples" / slug,
    ]
    for candidate in candidates:
        train = candidate / "train.py"
        if not train.is_file():
            continue
        # When resolving CWD, require a model.yaml whose model.id matches.
        model_yaml = candidate / "model.yaml"
        if candidate == Path.cwd():
            if not model_yaml.is_file():
                continue
            try:
                import yaml

                data = yaml.safe_load(model_yaml.read_text(encoding="utf-8")) or {}
                found = str((data.get("model") or {}).get("id", "")).replace("_", "-")
                if found not in {slug, model_id}:
                    continue
            except Exception:
                continue
        return candidate

    searched = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        f"No model source directory for {model_id!r} containing train.py. Searched: {searched}"
    )


def script_path(model_id: str, filename: str) -> str:
    path = model_source_dir(model_id) / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required script missing: {path}")
    return str(path)


def resource_tags(tags: dict[str, str]) -> list[dict[str, str]]:
    return [{"Key": k, "Value": v} for k, v in tags.items()]

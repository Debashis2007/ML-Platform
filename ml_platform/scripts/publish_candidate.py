#!/usr/bin/env python3
"""Write the candidate manifest the registration Lambda copies in (stdlib only).

Runs as the last pipeline step, only when every evaluation threshold passed. The
manifest binds the artefact checksum, the image digest, the metrics and the source
commit so the control plane can verify what it registers. It never registers anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_one(root: Path, pattern: str) -> Path:
    matches = sorted(root.rglob(pattern))
    if not matches:
        raise FileNotFoundError(f"{pattern} not found under {root}")
    return matches[0]


def build_manifest(args: argparse.Namespace) -> dict:
    if "@sha256:" not in args.image_uri:
        raise ValueError("ImageUri must be pinned by digest (repo@sha256:...)")
    artefact = find_one(Path(args.model_dir), "model.tar.gz")
    metrics = json.loads(find_one(Path(args.evaluation_dir), "metrics.json").read_text(encoding="utf-8"))
    thresholds = json.loads(args.thresholds)
    failed = {m: v for m, v in thresholds.items() if float(metrics.get(m, float("-inf"))) < float(v)}
    if failed:
        raise ValueError(f"Thresholds not met, refusing to publish candidate: {failed}")
    return {
        "schema_version": SCHEMA_VERSION,
        "tenant_id": args.tenant_id,
        "model_id": args.model_id,
        "model_package_group": args.model_package_group,
        "platform_version": args.platform_version,
        "source_account_id": args.source_account_id,
        "source_commit": args.source_commit,
        "image_uri": args.image_uri,
        "model_data_url": args.model_data_url,
        "model_data_sha256": sha256_file(artefact),
        "model_data_bytes": artefact.stat().st_size,
        "metrics": metrics,
        "thresholds": thresholds,
        "lineage_source_package_arn": args.lineage_source_package_arn or None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="/opt/ml/processing/model")
    parser.add_argument("--evaluation-dir", default="/opt/ml/processing/evaluation")
    parser.add_argument("--output-dir", default="/opt/ml/processing/output")
    parser.add_argument("--model-data-url", required=True)
    parser.add_argument("--image-uri", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-package-group", required=True)
    parser.add_argument("--platform-version", required=True)
    parser.add_argument("--source-account-id", required=True)
    parser.add_argument("--thresholds", required=True, help="JSON object metric -> minimum")
    parser.add_argument("--lineage-source-package-arn", default="")
    args, _unknown = parser.parse_known_args()

    manifest = build_manifest(args)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidate.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"candidate": manifest["model_data_sha256"], "model_id": manifest["model_id"]}))


if __name__ == "__main__":
    main()

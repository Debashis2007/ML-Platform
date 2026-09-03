#!/usr/bin/env python3
"""Assemble and upsert a SageMaker Pipeline from pipeline.yaml (ML Platform factory).

Usage:
  python ml_platform/build_pipeline.py --config examples/credit-risk/pipeline.yaml
  python ml_platform/build_pipeline.py --config pipeline.yaml --upsert --role-arn arn:...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_platform.config import PipelineConfig
from ml_platform.steps import build_steps


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ML Platform SageMaker Pipeline")
    parser.add_argument("--config", default="pipeline.yaml", help="Path to pipeline.yaml")
    parser.add_argument("--role-arn", default=None, help="SageMaker pipeline execution role ARN")
    parser.add_argument("--upsert", action="store_true", help="Call Pipeline.upsert()")
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    cfg = PipelineConfig.load(args.config)
    pipeline = build_steps(cfg, role_arn=args.role_arn)

    print(f"Pipeline name: {cfg.model_name}")
    print(f"Steps: {[s.name for s in pipeline.steps]}")
    print(f"Deployment target: {cfg.deployment_target}")
    print(f"Register gate: {cfg.threshold_metric} >= {cfg.threshold_min}")

    if args.upsert:
        if not args.role_arn:
            raise SystemExit("--role-arn required with --upsert")
        pipeline.upsert(role_arn=args.role_arn)
        print("Upserted successfully.")


if __name__ == "__main__":
    main()

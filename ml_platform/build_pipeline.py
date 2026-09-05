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

from botocore.exceptions import ClientError

from ml_platform.config import PipelineConfig
from ml_platform.logging_utils import log_json, setup_logging
from ml_platform.steps import build_steps

logger = setup_logging("ml_platform.build_pipeline")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ML Platform SageMaker Pipeline")
    parser.add_argument("--config", default="pipeline.yaml", help="Path to pipeline.yaml")
    parser.add_argument("--role-arn", default=None, help="SageMaker pipeline execution role ARN")
    parser.add_argument("--upsert", action="store_true", help="Call Pipeline.upsert()")
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    import os

    # SageMaker SDK requires a region even for definition-only builds.
    if args.region:
        os.environ["AWS_DEFAULT_REGION"] = args.region
        os.environ["AWS_REGION"] = args.region
    else:
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
        os.environ.setdefault("AWS_REGION", os.environ["AWS_DEFAULT_REGION"])

    try:
        cfg = PipelineConfig.load(args.config)
        pipeline = build_steps(cfg, role_arn=args.role_arn)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Pipeline build failed: %s", exc)
        raise SystemExit(2) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Pipeline build failed: %s", exc)
        raise SystemExit(2) from exc

    log_json(
        logger,
        "pipeline_built",
        pipeline_name=cfg.model_name,
        steps=[s.name for s in pipeline.steps],
        deployment_target=cfg.deployment_target,
        threshold_metric=cfg.threshold_metric,
        threshold_min=cfg.threshold_min,
        features_enabled=cfg.features_enabled,
        model_package_group=cfg.model_package_group,
    )

    if args.upsert:
        if not args.role_arn:
            raise SystemExit("--role-arn required with --upsert")
        try:
            pipeline.upsert(role_arn=args.role_arn)
        except ClientError as exc:
            logger.error("Pipeline upsert failed: %s", exc)
            raise SystemExit(1) from exc
        log_json(logger, "pipeline_upserted", pipeline_name=cfg.model_name, role_arn=args.role_arn)


if __name__ == "__main__":
    main()

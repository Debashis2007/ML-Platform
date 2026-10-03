#!/usr/bin/env python3
"""Assemble and upsert a SageMaker Pipeline from model.yaml (ML Platform factory).

Usage:
  python ml_platform/build_pipeline.py --config examples/credit-risk/model.yaml
  python ml_platform/build_pipeline.py --config model.yaml --upsert

The pipeline is upserted in the training account named by aws.account_id using
aws.pipeline_role_arn. The caller's credentials must already be in that account.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from botocore.exceptions import ClientError

from ml_platform.aws_client import client as aws_client
from ml_platform.config import ModelConfig
from ml_platform.logging_utils import log_json, setup_logging
from ml_platform.steps import build_steps
from ml_platform.steps.common import resource_tags

logger = setup_logging("ml_platform.build_pipeline")


def assert_training_account(cfg: ModelConfig, region: str | None = None) -> str:
    """Refuse to act when the caller is not in the configured training account."""
    caller = aws_client("sts", region_name=region or cfg.region).get_caller_identity()["Account"]
    if caller != cfg.account_id:
        raise SystemExit(
            f"Caller account {caller} does not match aws.account_id {cfg.account_id} "
            f"(training_target={cfg.training_target}); assume the training-account role first"
        )
    return caller


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ML Platform SageMaker Pipeline")
    parser.add_argument("--config", default="model.yaml", help="Path to model.yaml")
    parser.add_argument("--stage", choices=["nonprod", "prod"], default="nonprod",
                        help="prod = retrain in the Prod control plane (aws.prod)")
    parser.add_argument("--role-arn", default=None, help="Override aws.pipeline_role_arn")
    parser.add_argument("--upsert", action="store_true", help="Call Pipeline.upsert()")
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    try:
        cfg = ModelConfig.load(args.config, stage=args.stage)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("model.yaml invalid: %s", exc)
        raise SystemExit(2) from exc

    region = args.region or cfg.region
    # SageMaker SDK requires a region even for definition-only builds.
    os.environ["AWS_DEFAULT_REGION"] = region
    os.environ["AWS_REGION"] = region
    role_arn = args.role_arn or cfg.pipeline_role_arn

    try:
        pipeline = build_steps(cfg, role_arn=role_arn)
    except Exception as exc:  # noqa: BLE001
        logger.error("Pipeline build failed: %s", exc)
        raise SystemExit(2) from exc

    log_json(
        logger,
        "pipeline_built",
        pipeline_name=pipeline.name,
        steps=[s.name for s in pipeline.steps],
        training_target=cfg.training_target,
        account_id=cfg.account_id,
        thresholds=cfg.thresholds,
        model_package_group=cfg.model_package_group,
        tags=cfg.tags(),
    )

    if args.upsert:
        assert_training_account(cfg, region)
        try:
            pipeline.upsert(role_arn=role_arn, tags=resource_tags(cfg.tags()))
        except ClientError as exc:
            logger.error("Pipeline upsert failed: %s", exc)
            raise SystemExit(1) from exc
        log_json(logger, "pipeline_upserted", pipeline_name=pipeline.name, role_arn=role_arn)


if __name__ == "__main__":
    main()

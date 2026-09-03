#!/usr/bin/env python3
"""Start a SageMaker Pipeline execution (GHA → pipeline trigger)."""

from __future__ import annotations

import argparse
import json
import sys

import boto3


def main() -> None:
    parser = argparse.ArgumentParser(description="Start SageMaker pipeline execution")
    parser.add_argument("--pipeline-name", required=True)
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--image-uri", required=True)
    parser.add_argument("--data-uri", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--region", default=None)
    args = parser.parse_args()

    client = boto3.client("sagemaker", region_name=args.region)
    response = client.start_pipeline_execution(
        PipelineName=args.pipeline_name,
        PipelineExecutionDisplayName=f"{args.pipeline_name}-gha",
        PipelineParameters=[
            {"Name": "ImageUri", "Value": args.image_uri},
            {"Name": "DataUri", "Value": args.data_uri},
            {"Name": "OutputPrefix", "Value": args.output_prefix},
        ],
    )
    print(json.dumps(response, default=str))
    arn = response.get("PipelineExecutionArn")
    if not arn:
        sys.exit("PipelineExecutionArn missing from response")


if __name__ == "__main__":
    main()

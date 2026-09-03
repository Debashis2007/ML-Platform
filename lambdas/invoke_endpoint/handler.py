"""Invoke SageMaker endpoint."""

import json
import os

import boto3


def handler(event, context):
    endpoint = os.environ["ENDPOINT_NAME"]
    body = event.get("body")
    if isinstance(body, str):
        payload = body
    else:
        payload = json.dumps(event.get("features", event))
    client = boto3.client("sagemaker-runtime")
    response = client.invoke_endpoint(
        EndpointName=endpoint,
        ContentType="application/json",
        Body=payload,
    )
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": response["Body"].read().decode(),
    }

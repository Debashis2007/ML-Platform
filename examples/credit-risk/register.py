#!/usr/bin/env python3
"""Register model package in central SageMaker Model Registry (Pending Approval)."""

import argparse
import json
import os
from datetime import datetime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", default="/opt/ml/processing/model")
    args = parser.parse_args()

    package_group = os.environ.get("MODEL_PACKAGE_GROUP", "ModelCreditRisk")
    approval = os.environ.get("MODEL_APPROVAL_STATUS", "PendingManualApproval")
    image_uri = os.environ.get("INFERENCE_IMAGE_URI", "")
    model_data_url = os.environ.get("MODEL_DATA_URL", "")

    record = {
        "model_package_group_name": package_group,
        "model_approval_status": approval,
        "inference_specification": {
            "containers": [{"Image": image_uri, "ModelDataUrl": model_data_url}],
        },
        "registered_at": datetime.utcnow().isoformat() + "Z",
        "note": "ML Platform — register via SageMaker SDK in CI with hub account role",
    }
    print(json.dumps(record, indent=2))
    # In deployed CI: boto3 client('sagemaker').create_model_package(...)


if __name__ == "__main__":
    main()

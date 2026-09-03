import json
import os
from datetime import datetime, timezone

import boto3


def handler(event, context):
    """Capture Model Package state change → DynamoDB; publish deploy signal on Approved.

    LLD flow 11: registry approval → EventBridge → Lambda → DynamoDB → Workflow B.
    """
    detail = event.get("detail", event)
    table_name = os.environ.get("GOVERNANCE_TABLE", "MLPlatformStageGovernance")
    deploy_prefix = os.environ.get("DEPLOY_PARAMETER_PREFIX", "/mlp/deploy")

    group = detail.get("ModelPackageGroupName", "unknown")
    version = detail.get("ModelPackageVersion", datetime.now(timezone.utc).isoformat())
    package_arn = detail.get("ModelPackageArn", "")

    record = {
        "pk": group,
        "sk": str(version),
        "model_package_arn": package_arn,
        "approval_status": detail.get("ModelApprovalStatus"),
        "account": event.get("account", ""),
        "region": event.get("region", ""),
        "source": event.get("source", "aws.sagemaker"),
        "raw": json.dumps(detail)[:3500],
    }
    boto3.resource("dynamodb").Table(table_name).put_item(Item=record)

    if detail.get("ModelApprovalStatus") == "Approved" and package_arn:
        ssm = boto3.client("ssm")
        ssm.put_parameter(
            Name=f"{deploy_prefix}/model_package_arn",
            Value=package_arn,
            Type="String",
            Overwrite=True,
        )
        boto3.client("events").put_events(
            Entries=[
                {
                    "Source": "ml.platform.governance",
                    "DetailType": "Model Approved",
                    "Detail": json.dumps(
                        {
                            "model_package_arn": package_arn,
                            "model_package_group": group,
                            "model_package_version": version,
                        }
                    ),
                }
            ]
        )

    return {"statusCode": 200, "body": json.dumps(record)}

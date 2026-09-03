import json
import os
from datetime import datetime, timezone

import boto3


def handler(event, context):
    """Capture Model Package state change → DynamoDB (hub governance stack).

    EventBridge → Lambda → DynamoDB audit trail.
    Table name from env GOVERNANCE_TABLE (default: MLPlatformStageGovernance).
    """
    detail = event.get("detail", event)
    table_name = os.environ.get("GOVERNANCE_TABLE", "MLPlatformStageGovernance")
    record = {
        "pk": detail.get("ModelPackageGroupName", "unknown"),
        "sk": detail.get("ModelPackageVersion", datetime.now(timezone.utc).isoformat()),
        "approval_status": detail.get("ModelApprovalStatus"),
        "account": event.get("account", ""),
        "region": event.get("region", ""),
        "source": event.get("source", "aws.sagemaker"),
        "raw": json.dumps(detail)[:3500],
    }
    boto3.resource("dynamodb").Table(table_name).put_item(Item=record)
    return {"statusCode": 200, "body": json.dumps(record)}

"""AWS Architecture-style service icons for matplotlib / PowerPoint diagrams.

Optional: place official AWS Architecture Icons under
`assets/AWS_Architecture_Icons/Architecture-Service-Icons_04302026/`.
When icons are missing, diagrams fall back to colored abbreviation tiles.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import matplotlib.image as mpimg
from matplotlib.patches import Rectangle

BLACK = "#1C1C1C"

_REPO_ROOT = Path(__file__).resolve().parents[2]
ICON_ROOT = _REPO_ROOT / "assets" / "AWS_Architecture_Icons" / "Architecture-Service-Icons_04302026"

AWS_COLORS = {
    "s3": "#7AA116",
    "glue": "#01A88D",
    "lf": "#DD344C",
    "bedrock": "#01A88D",
    "opensearch": "#01A88D",
    "kms": "#DD344C",
    "eventbridge": "#ED7100",
    "lambda": "#ED7100",
    "dms": "#527FFF",
    "network": "#8C4FFF",
    "cognito": "#DD344C",
    "iam": "#DD344C",
    "control": "#ED7100",
    "cloudformation": "#DD344C",
    "rds": "#527FFF",
    "vpc": "#8C4FFF",
    "route53": "#8C4FFF",
}

ICON_FILES = {
    "s3": "Arch_Storage/32/Arch_Amazon-Simple-Storage-Service_32.png",
    "glue": "Arch_Analytics/32/Arch_AWS-Glue_32.png",
    "lf": "Arch_Analytics/32/Arch_AWS-Lake-Formation_32.png",
    "bedrock": "Arch_Artificial-Intelligence/32/Arch_Amazon-Bedrock_32.png",
    "bedrock_agent": "Arch_Artificial-Intelligence/32/Arch_Amazon-Bedrock-AgentCore_32.png",
    "opensearch": "Arch_Analytics/32/Arch_Amazon-OpenSearch-Service_32.png",
    "kms": "Arch_Security-Identity/32/Arch_AWS-Key-Management-Service_32.png",
    "eventbridge": "Arch_Application-Integration/32/Arch_Amazon-EventBridge_32.png",
    "lambda": "Arch_Compute/32/Arch_AWS-Lambda_32.png",
    "dms": "Arch_Databases/32/Arch_AWS-Database-Migration-Service_32.png",
    "network": "Arch_Networking-Content-Delivery/32/Arch_AWS-Transit-Gateway_32.png",
    "firewall": "Arch_Security-Identity/32/Arch_AWS-Network-Firewall_32.png",
    "privatelink": "Arch_Networking-Content-Delivery/32/Arch_AWS-PrivateLink_32.png",
    "cognito": "Arch_Security-Identity/32/Arch_Amazon-Cognito_32.png",
    "identity_center": "Arch_Security-Identity/32/Arch_AWS-IAM-Identity-Center_32.png",
    "iam": "Arch_Security-Identity/32/Arch_AWS-Identity-and-Access-Management_32.png",
    "api_gateway": "Arch_Networking-Content-Delivery/32/Arch_Amazon-API-Gateway_32.png",
    "cloudformation": "Arch_Management-Tools/32/Arch_AWS-CloudFormation_32.png",
    "rds": "Arch_Databases/32/Arch_Amazon-RDS_32.png",
    "dynamodb": "Arch_Databases/32/Arch_Amazon-DynamoDB_32.png",
    "vpc": "Arch_Networking-Content-Delivery/32/Arch_Amazon-Virtual-Private-Cloud_32.png",
    "route53": "Arch_Networking-Content-Delivery/32/Arch_Amazon-Route-53_32.png",
    "control_tower": "Arch_Management-Tools/32/Arch_AWS-Control-Tower_32.png",
    "organizations": "Arch_Management-Tools/32/Arch_AWS-Organizations_32.png",
    "cloudwatch": "Arch_Management-Tools/32/Arch_Amazon-CloudWatch_32.png",
    "codecommit": "Arch_Developer-Tools/32/Arch_AWS-CodeCommit_32.png",
    "codeartifact": "Arch_Developer-Tools/32/Arch_AWS-CodeArtifact_32.png",
    "xray": "Arch_Developer-Tools/32/Arch_AWS-X-Ray_32.png",
    "eks": "Arch_Containers/32/Arch_Amazon-Elastic-Kubernetes-Service_32.png",
    "ecs": "Arch_Containers/32/Arch_Amazon-Elastic-Container-Service_32.png",
    "ecr": "Arch_Containers/32/Arch_Amazon-Elastic-Container-Registry_32.png",
    "inspector": "Arch_Security-Identity/32/Arch_Amazon-Inspector_32.png",
    "shield": "Arch_Security-Identity/32/Arch_AWS-Shield_32.png",
    "sagemaker": "Arch_Artificial-Intelligence/32/Arch_Amazon-SageMaker-AI_32.png",
    "athena": "Arch_Analytics/32/Arch_Amazon-Athena_32.png",
    "aurora": "Arch_Databases/32/Arch_Amazon-Aurora_32.png",
    "direct_connect": "Arch_Networking-Content-Delivery/32/Arch_AWS-Direct-Connect_32.png",
    "vpn": "Arch_Networking-Content-Delivery/32/Arch_AWS-Site-to-Site-VPN_32.png",
    "secrets_manager": "Arch_Security-Identity/32/Arch_AWS-Secrets-Manager_32.png",
    "elb": "Arch_Networking-Content-Delivery/32/Arch_Elastic-Load-Balancing_32.png",
    "sns": "Arch_Application-Integration/32/Arch_Amazon-Simple-Notification-Service_32.png",
    "step_functions": "Arch_Application-Integration/32/Arch_AWS-Step-Functions_32.png",
    "codebuild": "Arch_Developer-Tools/32/Arch_AWS-CodeBuild_32.png",
    "quicksight": "Arch_Business-Applications/32/Arch_Amazon-Quick_32.png",
    "elasticache": "Arch_Databases/32/Arch_Amazon-ElastiCache_32.png",
}

ABBR_TO_ICON_KEY = {
    "S3": "s3",
    "Gl": "glue",
    "LF": "lf",
    "Br": "bedrock",
    "OS": "opensearch",
    "KMS": "kms",
    "EB": "eventbridge",
    "DMS": "dms",
    "\u03bb": "lambda",
    "TGW": "network",
    "FW": "firewall",
    "PL": "privatelink",
    "Cg": "cognito",
    "IC": "identity_center",
    "IAM": "iam",
    "GW": "api_gateway",
    "AA": "bedrock_agent",
    "CF": "cloudformation",
    "RDS": "rds",
    "DDB": "dynamodb",
    "Dyn": "dynamodb",
    "VPC": "vpc",
    "R53": "route53",
    "CT": "control_tower",
    "Org": "organizations",
    "CW": "cloudwatch",
    "CC": "codecommit",
    "CA": "codeartifact",
    "XR": "xray",
    "EKS": "eks",
    "ECS": "ecs",
    "ECR": "ecr",
    "Insp": "inspector",
    "Shd": "shield",
    "SM": "sagemaker",
    "Ath": "athena",
    "Aur": "aurora",
    "DC": "direct_connect",
    "VPN": "vpn",
    "SecM": "secrets_manager",
    "Lam": "lambda",
    "Cog": "cognito",
    "APIGW": "api_gateway",
    "GH": "codecommit",
    "ALB": "elb",
    "ELB": "elb",
    "LB": "elb",
    "SNS": "sns",
    "SFN": "step_functions",
    "CB": "codebuild",
    "QS": "quicksight",
    "EC": "elasticache",
    "FS": "elasticache",
}

PROVIDER_SERVICES = [
    ("S3", "Amazon S3", AWS_COLORS["s3"]),
    ("RDS", "Amazon RDS\nPostgres", AWS_COLORS["rds"]),
    ("Gl", "AWS Glue", AWS_COLORS["glue"]),
    ("LF", "Lake\nFormation", AWS_COLORS["lf"]),
    ("Br", "Amazon\nBedrock", AWS_COLORS["bedrock"]),
    ("OS", "OpenSearch\nServerless", AWS_COLORS["opensearch"]),
    ("KMS", "KMS · Secrets\nManager", AWS_COLORS["kms"]),
    ("EB", "Event\nBridge", AWS_COLORS["eventbridge"]),
]


@lru_cache(maxsize=None)
def _load_icon(rel_path: str):
    path = ICON_ROOT / rel_path
    return mpimg.imread(path)


def _draw_real_icon(ax, x, y, size, icon_key) -> bool:
    rel_path = ICON_FILES.get(icon_key)
    if not rel_path:
        return False
    try:
        img = _load_icon(rel_path)
    except (FileNotFoundError, OSError):
        return False
    ax.imshow(img, extent=(x, x + size, y, y + size), zorder=5, aspect="auto")
    return True


def aws_icon(ax, x, y, abbr, color, size=0.38, fs=7.0, text_color="white"):
    icon_key = ABBR_TO_ICON_KEY.get(abbr)
    if not (icon_key and _draw_real_icon(ax, x, y, size, icon_key)):
        ax.add_patch(Rectangle((x, y), size, size, facecolor=color, edgecolor=BLACK, linewidth=0.7))
        ax.text(x + size / 2, y + size / 2, abbr, ha="center", va="center", fontsize=fs, color=text_color, weight="bold")
    return {"x": x, "y": y, "w": size, "h": size, "cx": x + size / 2}

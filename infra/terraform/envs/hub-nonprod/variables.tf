variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "mlp-hub-nonprod"
}

variable "vpc_id" {
  type        = string
  description = "Existing hub VPC ID."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnets for SageMaker."
}

variable "enable_vpc_endpoints" {
  type        = bool
  default     = true
  description = "Create S3/SageMaker/ECR/Logs/STS/CloudWatch VPC endpoints for private ML traffic."
}

variable "data_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for training data."
}

variable "artifacts_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for artifacts."
}

variable "ecr_repository_name" {
  type    = string
  default = "ml-platform-models"
}

variable "model_package_group_name" {
  type    = string
  default = "ModelCreditRisk"
}

variable "spoke_account_ids" {
  type        = list(string)
  default     = []
  description = "Dev/test spoke account IDs for RAM model package sharing."
}

# --- Client-managed IAM role ARNs (roles are NOT created by Terraform) ---

variable "pipeline_role_arn" {
  type        = string
  description = "SageMaker pipeline execution role ARN (client-managed)."
}

variable "training_role_arn" {
  type        = string
  description = "SageMaker training/processing role ARN (client-managed)."
}

variable "inference_role_arn" {
  type        = string
  default     = ""
  description = "SageMaker inference role ARN (required when endpoints are enabled)."
}

variable "governance_lambda_role_arn" {
  type        = string
  description = "Lambda role for capture_approval (client-managed)."
}

variable "github_dispatch_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Lambda role for github_dispatch (required when enable_auto_deploy)."
}

variable "stage_export_lambda_role_arn" {
  type        = string
  description = "Lambda role for Stage Governance S3 export (client-managed)."
}

variable "dev_artifacts_bucket_name" {
  type        = string
  description = "Dev artifacts bucket for pipeline build outputs."
}

variable "athena_spill_bucket_name" {
  type        = string
  description = "Globally unique bucket for Athena spill + Stage Governance exports."
}

variable "quicksight_user_arn" {
  type        = string
  default     = ""
  description = "Optional QuickSight user ARN. Leave empty if CRBG BI uses Power BI → Athena."
}

variable "enable_auto_deploy" {
  type        = bool
  default     = false
  description = "Wire Model Approved → GitHub repository_dispatch (requires github_* vars + token)."
}

variable "github_owner" {
  type    = string
  default = ""
}

variable "github_repo" {
  type    = string
  default = ""
}

variable "github_dispatch_token" {
  type        = string
  default     = ""
  sensitive   = true
  description = "GitHub PAT or App token with repo dispatch scope. Prefer TF_VAR_github_dispatch_token."

  validation {
    condition     = !var.enable_auto_deploy || (var.github_dispatch_token != "" && var.github_owner != "" && var.github_repo != "")
    error_message = "enable_auto_deploy requires github_dispatch_token, github_owner, and github_repo."
  }
}

variable "tags" {
  type    = map(string)
  default = { Environment = "hub-nonprod", Plane = "central-nonprod", ManagedBy = "terraform" }
}

# --- Design v7 ---

variable "bu" {
  type        = string
  default     = "platform"
  description = "Default tag: owning BU."
}

variable "project" {
  type        = string
  default     = "ml-platform"
  description = "Default tag: project."
}

variable "platform_version" {
  type        = string
  default     = "v1.0.0"
  description = "Default tag: platform version."
}

variable "model_ids" {
  type        = list(string)
  default     = ["credit-risk"]
  description = "Models that get an immutable per-model ECR repository."
}

variable "training_account_ids" {
  type        = list(string)
  default     = []
  description = "BU accounts allowed to submit candidates (empty while training runs on the control plane)."
}

variable "deployment_account_ids" {
  type        = list(string)
  default     = []
  description = "Deployment target accounts allowed to pull model images by digest."
}

variable "source_read_role_name" {
  type        = string
  default     = ""
  description = "Role name in BU training accounts the registration Lambda assumes (BU training only)."
}

variable "break_glass_principal_arns" {
  type        = list(string)
  default     = []
  description = "Principals exempt from the Object Lock bucket delete/retention deny."
}

variable "registration_lambda_role_arn" {
  type        = string
  description = "Client-managed role for the copy-in registration Lambda (denied sagemaker:UpdateModelPackage)."
}

variable "enable_management_api" {
  type        = bool
  default     = true
  description = "Private management API (approval path). Needs platform Lambda images from CI."
}

variable "approval_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Client-managed role for the approval Lambda (the only UpdateModelPackage principal)."
}

variable "authorizer_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Client-managed role for the Okta authorizer Lambda."
}

variable "okta_issuer" {
  type        = string
  default     = ""
  description = "Okta authorization server issuer URL."

  validation {
    condition     = !var.enable_management_api || var.okta_issuer != ""
    error_message = "okta_issuer is required when enable_management_api is true."
  }
}

variable "okta_audience" {
  type    = string
  default = "api://ml-platform-management"
}

variable "waf_web_acl_arn" {
  type        = string
  default     = ""
  description = "Optional Web ACL for the management API stage (replaceable protection hook)."
}

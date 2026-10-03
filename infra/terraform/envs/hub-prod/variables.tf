variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "mlp-hub-prod"
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "enable_vpc_endpoints" {
  type        = bool
  default     = true
  description = "Create S3/SageMaker/ECR/Logs/STS/CloudWatch VPC endpoints for private ML traffic."
}

variable "data_bucket_name" {
  type = string
}

variable "prod_data_bucket_name" {
  type = string
}

variable "artifacts_bucket_name" {
  type = string
}

variable "dev_artifacts_bucket_name" {
  type = string
}

variable "ecr_repository_name" {
  type    = string
  default = "ml-platform-models"
}

variable "model_package_group_name" {
  type    = string
  default = "ModelCreditRisk"
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
  description = "SageMaker inference role ARN (required when BU endpoints enabled)."
}

variable "governance_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Required when enable_governance=true."
}

variable "github_dispatch_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Required when enable_auto_deploy=true."
}

variable "stage_export_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Required when enable_governance=true (Stage Analytics export)."
}

variable "promote_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Required when enable_promote=true."
}

variable "create_registry" {
  type        = bool
  default     = true
  description = "Create PROD model package group (one registry per Central Plane env)."
}

variable "enable_governance" {
  type        = bool
  default     = true
  description = "Enable Stage Governance in the PROD Central Plane account."
}

variable "enable_auto_deploy" {
  type    = bool
  default = false
}

variable "enable_promote" {
  type        = bool
  default     = true
  description = "Deploy promote Lambda for Non-Prod → Prod registry promotion."
}

variable "athena_spill_bucket_name" {
  type        = string
  default     = ""
  description = "Required when enable_governance=true."

  validation {
    condition     = !var.enable_governance || var.athena_spill_bucket_name != ""
    error_message = "athena_spill_bucket_name is required when enable_governance is true."
  }
}

variable "quicksight_user_arn" {
  type    = string
  default = ""
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
  type      = string
  default   = ""
  sensitive = true
}

variable "spoke_account_ids" {
  type    = list(string)
  default = []
}


variable "tags" {
  type    = map(string)
  default = { Environment = "hub-prod", Plane = "central-prod", ManagedBy = "terraform" }
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

variable "source_registry_read_role_arn" {
  type        = string
  default     = ""
  description = "Read-only role in Control-NonProd the promote Lambda assumes to verify the NonProd approval."
}

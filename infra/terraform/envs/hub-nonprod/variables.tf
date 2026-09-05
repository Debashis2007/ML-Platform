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

variable "step_functions_role_arn" {
  type        = string
  description = "Step Functions role for pipeline trigger (client-managed)."
}

variable "dev_artifacts_bucket_name" {
  type        = string
  description = "Dev artifacts bucket for pipeline build outputs."
}

variable "create_dev_test_endpoint" {
  type    = bool
  default = false
}

variable "dev_test_model_package_arn" {
  type    = string
  default = ""
}

variable "enable_bu_endpoints" {
  type        = bool
  default     = false
  description = "Create Central Plane DEV BU endpoints (BU1/BU2/BU3/BU4) without API Gateway."
}

variable "business_units" {
  type = map(object({
    endpoint_name       = string
    model_package_arn   = string
    instance_type       = optional(string, "ml.m5.large")
    instance_count      = optional(number, 1)
    enable_data_capture = optional(bool, true)
    enable_multi_az     = optional(bool, false)
  }))
  default = {
    BU1 = { endpoint_name = "bu1-credit-risk-dev", model_package_arn = "" }
    BU2 = { endpoint_name = "bu2-credit-risk-dev", model_package_arn = "" }
    BU3 = { endpoint_name = "bu3-credit-risk-dev", model_package_arn = "" }
    BU4 = { endpoint_name = "bu4-credit-risk-dev", model_package_arn = "" }
  }
  description = "BU endpoint map. Set model_package_arn per BU to materialize that endpoint."
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

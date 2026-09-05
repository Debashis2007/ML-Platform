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

variable "step_functions_role_arn" {
  type        = string
  description = "Step Functions role for pipeline trigger (client-managed)."
}

variable "promote_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Required when enable_promote=true."
}

variable "invoke_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Required when enable_bu_endpoints=true (API invoke Lambda)."
}

variable "apigateway_cloudwatch_role_arn" {
  type        = string
  default     = ""
  description = "Required when enable_bu_endpoints=true (API Gateway account CloudWatch role)."
}

variable "create_registry" {
  type        = bool
  default     = true
  description = "Create PROD model package group (platform: one registry per Central Plane env)."
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

variable "enable_bu_endpoints" {
  type        = bool
  default     = false
  description = "Create Prod BU endpoints with API Gateway."
}

variable "enable_waf" {
  type    = bool
  default = true
}

variable "business_units" {
  type = map(object({
    endpoint_name       = string
    model_package_arn   = string
    instance_type       = optional(string, "ml.m5.large")
    instance_count      = optional(number, 1)
    enable_data_capture = optional(bool, true)
    enable_multi_az     = optional(bool, true)
  }))
  default = {
    BU1 = { endpoint_name = "bu1-credit-risk", model_package_arn = "" }
    BU2 = { endpoint_name = "bu2-credit-risk", model_package_arn = "" }
    BU3 = { endpoint_name = "bu3-credit-risk", model_package_arn = "" }
    BU4 = { endpoint_name = "bu4-credit-risk", model_package_arn = "" }
  }
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

variable "endpoint_name" {
  type    = string
  default = "credit-risk"
}

variable "tags" {
  type    = map(string)
  default = { Environment = "hub-prod", Plane = "central-prod", ManagedBy = "terraform" }
}

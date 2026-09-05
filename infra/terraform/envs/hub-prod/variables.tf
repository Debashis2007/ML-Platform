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

variable "create_iam_roles" {
  type        = bool
  default     = false
  description = "Create IAM roles in this account. When false, pass pipeline_role_arn/training_role_arn."
}

variable "pipeline_role_arn" {
  type    = string
  default = ""
}

variable "training_role_arn" {
  type    = string
  default = ""
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

variable "inference_role_arn" {
  type        = string
  default     = ""
  description = "Required when create_iam_roles=false and enable_bu_endpoints=true."
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

variable "github_oidc_provider_arn" {
  type    = string
  default = null
}

variable "github_repo_subjects" {
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

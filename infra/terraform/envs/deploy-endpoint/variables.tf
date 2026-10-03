variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "mlp"
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

variable "model_package_arn" {
  type        = string
  description = "Model package ARN approved through the management API (release workflow input)."
}

variable "endpoint_name" {
  type    = string
  default = "credit-risk"
}

variable "inference_role_arn" {
  type        = string
  description = "Client-managed SageMaker inference role ARN."
}

variable "invoke_lambda_role_arn" {
  type        = string
  default     = ""
  description = "Client-managed invoke Lambda role ARN (required when enable_api_gateway)."
}

variable "apigateway_cloudwatch_role_arn" {
  type        = string
  default     = ""
  description = "Client-managed API Gateway CloudWatch role ARN (required when enable_api_gateway)."
}

variable "instance_type" {
  type    = string
  default = "ml.m5.large"
}

variable "instance_count" {
  type        = number
  default     = 2
  description = "Initial and minimum instances; LIVE requires at least 2."
}

variable "max_instance_count" {
  type    = number
  default = 4
}


variable "enable_api_gateway" {
  type        = bool
  description = "Private invoke API in the target account. Default off: consumers call SageMaker runtime through the VPC endpoint."
  default     = false
}

variable "business_unit" {
  type        = string
  default     = ""
  description = "BU code: BU1 | BU2 | BU3 | BU4"
}

variable "enable_api_iam_auth" {
  type        = bool
  description = "Require AWS IAM (SigV4) auth on the invoke API."
  default     = true
}



variable "kms_key_arn" {
  type        = string
  default     = null
  description = "CMK for SNS and endpoint data capture."
}

variable "artifacts_bucket_name" {
  type        = string
  default     = ""
  description = "Artifacts bucket used to derive data-capture URI when data_capture_s3_uri is empty."
}

variable "enable_data_capture" {
  type    = bool
  default = true
}

variable "data_capture_s3_uri" {
  type    = string
  default = ""
}

variable "data_capture_percentage" {
  type    = number
  default = 100
}

variable "enable_model_monitor" {
  type        = bool
  default     = false
  description = "Create SageMaker Data Quality monitoring schedule (requires baselines)."
}

variable "monitoring_role_arn" {
  type    = string
  default = ""
}

variable "baseline_constraints_s3_uri" {
  type    = string
  default = ""
}

variable "baseline_statistics_s3_uri" {
  type    = string
  default = ""
}

variable "monitoring_output_s3_uri" {
  type    = string
  default = ""
}

variable "monitoring_image_uri" {
  type        = string
  default     = ""
  description = "Region-specific Model Monitor analyzer image URI."
}

variable "alarm_actions" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = { ManagedBy = "terraform" }
}

# --- Design v7 release ---

variable "environment" {
  type        = string
  description = "qa (ALL_AT_ONCE) or live (CANARY 10%, 15-minute bake)."
}

variable "release_id" {
  type        = string
  description = "Unique per release; names the model and endpoint configuration."
}

variable "target_role_arn" {
  type        = string
  default     = ""
  description = "Optional deploy role in the target account to assume (client-managed)."
}

variable "waf_web_acl_arn" {
  type        = string
  default     = ""
  description = "Optional Web ACL for the invoke API stage (replaceable protection hook)."
}

variable "bu" {
  type    = string
  default = ""
}

variable "project" {
  type    = string
  default = "ml-platform"
}

variable "platform_version" {
  type    = string
  default = "v1.0.0"
}

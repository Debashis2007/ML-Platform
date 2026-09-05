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
  description = "Approved model package ARN from Workflow B trigger."
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
  type    = number
  default = 1
}

variable "enable_multi_az" {
  type    = bool
  default = false
}

variable "enable_api_gateway" {
  type        = bool
  description = "true = Prod front door. false = Non-Prod DEV (direct SageMaker invoke only)."
  default     = true
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

variable "enable_waf" {
  type        = bool
  default     = true
  description = "Associate a regional WAFv2 Web ACL with the API stage."
}

variable "waf_rate_limit" {
  type    = number
  default = 2000
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

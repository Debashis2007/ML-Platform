variable "name_prefix" {
  type = string
}

variable "endpoint_name" {
  type = string
}

variable "endpoint_arn" {
  type        = string
  description = "SageMaker endpoint ARN used to scope InvokeEndpoint IAM."
  default     = ""
}

variable "lambda_zip_path" {
  type        = string
  default     = ""
  description = "Path to invoke_endpoint Lambda zip (zip fallback when image URI empty)."
}

variable "lambda_source_hash" {
  type    = string
  default = ""
}

variable "invoke_endpoint_image_uri" {
  type        = string
  default     = ""
  description = "ECR image URI from platform-infra CI. When set, deploys container Lambda instead of zip."
}

variable "lambda_role_arn" {
  type        = string
  description = "Client-managed IAM role ARN for invoke_endpoint Lambda."
}

variable "endpoint_type" {
  type        = string
  default     = "PRIVATE"
  description = "PRIVATE (design v7, via execute-api VPC endpoint) or REGIONAL."

  validation {
    condition     = contains(["PRIVATE", "REGIONAL"], var.endpoint_type)
    error_message = "endpoint_type must be PRIVATE or REGIONAL."
  }
}

variable "vpc_endpoint_ids" {
  type        = list(string)
  default     = []
  description = "execute-api VPC endpoint IDs (required when PRIVATE)."
}

variable "enable_iam_auth" {
  type        = bool
  description = "Require SigV4 (AWS_IAM) on POST /invocations. Recommended for production."
  default     = true
}

variable "enable_access_logs" {
  type        = bool
  description = "Enable API Gateway access logging and INFO execution logs."
  default     = true
}

variable "throttling_burst_limit" {
  type    = number
  default = 100
}

variable "throttling_rate_limit" {
  type    = number
  default = 50
}

variable "model_version" {
  type        = string
  description = "Optional model version metadata returned by the invoke Lambda."
  default     = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "name_prefix" {
  type = string
}

variable "vpc_endpoint_ids" {
  type        = list(string)
  description = "execute-api interface endpoint IDs allowed to reach the private API."
}

variable "okta_issuer" {
  type        = string
  description = "Okta authorization server issuer URL."
}

variable "okta_audience" {
  type        = string
  description = "Expected aud claim."
}

variable "okta_required_scope" {
  type    = string
  default = "ml.approve"
}

variable "okta_authorizer_image_uri" {
  type        = string
  default     = ""
  description = "Container image for the authorizer (required: it bundles PyJWT)."
}

variable "approval_api_image_uri" {
  type    = string
  default = ""
}

variable "authorizer_lambda_role_arn" {
  type        = string
  description = "Client-managed role: logs and VPC access only."
}

variable "approval_lambda_role_arn" {
  type        = string
  description = "Client-managed role: the only principal with sagemaker:UpdateModelPackage, plus the four governance tables."
}

variable "lifecycle_table_name" {
  type = string
}

variable "decision_log_table_name" {
  type = string
}

variable "identity_table_name" {
  type = string
}

variable "locks_table_name" {
  type = string
}

variable "lock_ttl_seconds" {
  type    = number
  default = 120
}

variable "waf_web_acl_arn" {
  type        = string
  default     = ""
  description = "Optional Web ACL to associate with the stage (replaceable protection hook)."
}

variable "lambda_subnet_ids" {
  type    = list(string)
  default = []
}

variable "lambda_security_group_ids" {
  type    = list(string)
  default = []
}

variable "alarm_actions" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}

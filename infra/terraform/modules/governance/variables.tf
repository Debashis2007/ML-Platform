variable "name_prefix" {
  type = string
}

variable "model_package_group_name" {
  type = string
}

variable "lambda_source_dir" {
  type        = string
  description = "Path to capture_approval_event Lambda source (zip built at apply time)."
  default     = ""
}

variable "deploy_parameter_prefix" {
  type    = string
  default = ""
  description = "SSM prefix for latest approved model package ARN (Workflow B input)."
}

variable "tags" {
  type    = map(string)
  default = {}
}

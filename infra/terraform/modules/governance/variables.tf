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

variable "tags" {
  type    = map(string)
  default = {}
}

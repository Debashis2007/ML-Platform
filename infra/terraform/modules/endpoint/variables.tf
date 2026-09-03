variable "name_prefix" {
  type = string
}

variable "model_package_arn" {
  type        = string
  description = "Approved SageMaker Model Package ARN to deploy."
}

variable "endpoint_name" {
  type        = string
  description = "SageMaker endpoint name."
}

variable "inference_role_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
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

variable "tags" {
  type    = map(string)
  default = {}
}

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

variable "model_package_arn" {
  type        = string
  description = "Approved model package ARN from Workflow B trigger."
}

variable "endpoint_name" {
  type    = string
  default = "credit-risk"
}

variable "inference_role_arn" {
  type = string
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

variable "alarm_actions" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = { ManagedBy = "terraform" }
}

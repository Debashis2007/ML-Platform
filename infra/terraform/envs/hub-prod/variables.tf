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

variable "pipeline_role_arn" {
  type = string
}

variable "training_role_arn" {
  type = string
}

variable "endpoint_name" {
  type    = string
  default = "credit-risk"
}

variable "tags" {
  type    = map(string)
  default = { Environment = "hub-prod", ManagedBy = "terraform" }
}

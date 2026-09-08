variable "platform_ecr_registry" {
  type        = string
  default     = ""
  description = "ECR registry host from platform-infra CI (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com)."
}

variable "platform_lambda_image_tag" {
  type        = string
  default     = ""
  description = "Git SHA or tag suffix for platform Lambda images built in CI before CD apply."
}

variable "platform_lambdas_ecr_repository_name" {
  type        = string
  default     = "mlp-platform-lambdas"
  description = "ECR repository for platform Lambda container images."
}

module "platform_lambda_uris" {
  source = "../../modules/platform_lambda_uris"

  registry        = var.platform_ecr_registry
  image_tag       = var.platform_lambda_image_tag
  repository_name = var.platform_lambdas_ecr_repository_name
}

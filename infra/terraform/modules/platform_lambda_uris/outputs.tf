variable "registry" {
  type        = string
  default     = ""
  description = "ECR registry host (account.dkr.ecr.region.amazonaws.com). Empty disables image URIs."
}

variable "repository_name" {
  type        = string
  default     = "mlp-platform-lambdas"
  description = "ECR repository for platform Lambda container images."
}

variable "image_tag" {
  type        = string
  default     = ""
  description = "Image tag suffix (typically git SHA). Empty disables image URIs (zip fallback)."
}

locals {
  enabled = var.registry != "" && var.image_tag != ""
  prefix  = "${var.registry}/${var.repository_name}"
}

output "enabled" {
  value = local.enabled
}

output "capture_approval" {
  value = local.enabled ? "${local.prefix}:capture-approval-${var.image_tag}" : ""
}

output "github_dispatch" {
  value = local.enabled ? "${local.prefix}:github-dispatch-${var.image_tag}" : ""
}

output "promote_model" {
  value = local.enabled ? "${local.prefix}:promote-model-${var.image_tag}" : ""
}

output "invoke_endpoint" {
  value = local.enabled ? "${local.prefix}:invoke-endpoint-${var.image_tag}" : ""
}

output "governance_export" {
  value = local.enabled ? "${local.prefix}:governance-export-${var.image_tag}" : ""
}

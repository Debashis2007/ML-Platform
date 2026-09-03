variable "model_package_group_name" {
  type        = string
  description = "SageMaker Model Package Group name (one per model family)."
}

variable "description" {
  type    = string
  default = "ML Platform model package group"
}

variable "spoke_account_ids" {
  type        = list(string)
  default     = []
  description = "Spoke account IDs to share the model package group with via RAM."
}

variable "tags" {
  type    = map(string)
  default = {}
}

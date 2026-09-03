variable "name_prefix" {
  type        = string
  description = "Prefix for resource names."
}

variable "vpc_id" {
  type        = string
  description = "Existing VPC ID for SageMaker jobs and endpoints."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for SageMaker processing/training/inference."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to all resources."
}

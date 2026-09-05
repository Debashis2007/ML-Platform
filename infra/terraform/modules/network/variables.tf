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

variable "enable_vpc_endpoints" {
  type        = bool
  default     = true
  description = "Create Gateway (S3) and Interface (SageMaker/ECR/Logs/STS/CW) VPC endpoints."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to all resources."
}

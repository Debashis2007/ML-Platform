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

variable "plane" {
  type        = string
  default     = "control_plane"
  description = "control_plane or bu — selects the default interface endpoint set."

  validation {
    condition     = contains(["control_plane", "bu"], var.plane)
    error_message = "plane must be control_plane or bu."
  }
}

variable "enable_vpc_endpoints" {
  type        = bool
  default     = true
  description = "Create the S3 gateway and the interface endpoints for this plane."
}

variable "interface_services" {
  type        = list(string)
  default     = null
  description = "Override the interface endpoint services (e.g. [\"sagemaker.api\", \"ecr.dkr\"]). Null = plane default."
}

variable "enable_dynamodb_gateway" {
  type        = bool
  default     = null
  description = "DynamoDB gateway endpoint. Null = on for the control plane, off for BU."
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Tags applied to all resources."
}

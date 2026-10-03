variable "name_prefix" {
  type = string
}

variable "model_name" {
  type        = string
  description = "Model / pipeline name (matches model.yaml model.id)."
}

variable "pipeline_role_arn" {
  type = string
}

variable "training_role_arn" {
  type = string
}

variable "artifacts_bucket_name" {
  type = string
}

variable "data_bucket_name" {
  type = string
}

variable "metric_name" {
  type    = string
  default = "auc"
}

variable "metric_threshold" {
  type    = number
  default = 0.75
}

variable "train_instance_type" {
  type    = string
  default = "ml.m5.xlarge"
}

variable "evaluate_instance_type" {
  type    = string
  default = "ml.m5.xlarge"
}

variable "features_enabled" {
  type    = bool
  default = false
}

variable "model_package_group_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

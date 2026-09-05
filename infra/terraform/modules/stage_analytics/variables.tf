variable "name_prefix" {
  type = string
}

variable "governance_table_name" {
  type        = string
  description = "DynamoDB Stage Governance table name."
}

variable "governance_table_arn" {
  type = string
}

variable "kms_key_arn" {
  type    = string
  default = null
}

variable "spill_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket for Athena spill + governance exports."
}

variable "athena_database_name" {
  type    = string
  default = "ml_platform_governance"
}

variable "athena_workgroup_name" {
  type    = string
  default = ""
}

variable "export_schedule_expression" {
  type        = string
  default     = "rate(1 hour)"
  description = "EventBridge schedule for DynamoDB → S3 export used by Athena."
}

variable "quicksight_user_arn" {
  type        = string
  default     = ""
  description = "If set, create QuickSight Athena data source + dataset. Empty skips QS (Power BI can still use Athena JDBC)."
}

variable "aws_account_id" {
  type    = string
  default = ""
}

variable "aws_region" {
  type    = string
  default = ""
}

variable "tags" {
  type    = map(string)
  default = {}
}

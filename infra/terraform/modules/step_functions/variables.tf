variable "name_prefix" {
  type = string
}

variable "pipeline_name" {
  type = string
}

variable "pipeline_role_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

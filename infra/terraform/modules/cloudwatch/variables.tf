variable "name_prefix" {
  type = string
}

variable "endpoint_name" {
  type    = string
  default = ""
}

variable "pipeline_names" {
  type    = list(string)
  default = []
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "name_prefix" {
  type = string
}

variable "description" {
  type    = string
  default = "ML Platform pipeline secrets"
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "name_prefix" {
  type = string
}

variable "endpoint_name" {
  type = string
}

variable "lambda_zip_path" {
  type        = string
  description = "Path to invoke_endpoint Lambda zip."
}

variable "lambda_source_hash" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "name_prefix" {
  type = string
}

variable "rate_limit" {
  type        = number
  default     = 2000
  description = "Requests per 5-minute window per IP before rate-based rule blocks."
}

variable "enable_managed_rules" {
  type        = bool
  default     = true
  description = "Attach AWSManagedRulesCommonRuleSet and KnownBadInputsRuleSet."
}

variable "resource_arns" {
  type        = list(string)
  description = "ARNs to associate (API Gateway stage ARN, ALB, etc.)."
  default     = []
}

variable "tags" {
  type    = map(string)
  default = {}
}

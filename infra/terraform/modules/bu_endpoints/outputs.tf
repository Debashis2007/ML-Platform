output "endpoint_names" {
  value = { for bu, m in module.endpoint : bu => m.endpoint_name }
}

output "endpoint_arns" {
  value = { for bu, m in module.endpoint : bu => m.endpoint_arn }
}

output "api_invoke_urls" {
  value = { for bu, m in module.api_gateway : bu => m.invoke_url }
}

output "waf_web_acl_arns" {
  value = { for bu, m in module.waf : bu => m.web_acl_arn }
}

output "active_business_units" {
  value = keys(local.active_bus)
}

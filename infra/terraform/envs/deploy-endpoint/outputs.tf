output "endpoint_name" {
  value = module.endpoint.endpoint_name
}

output "endpoint_arn" {
  value = module.endpoint.endpoint_arn
}

output "api_invoke_url" {
  value = try(module.api_gateway[0].invoke_url, null)
}

output "sns_alerts_topic_arn" {
  value = module.sns.alerts_topic_arn
}

output "waf_web_acl_arn" {
  value = try(module.waf[0].web_acl_arn, null)
}

output "monitoring_schedule_name" {
  value = module.monitoring.monitoring_schedule_name
}

output "data_capture_s3_uri" {
  value = local.data_capture_uri
}

output "business_unit" {
  value = var.business_unit
}

output "enable_api_gateway" {
  value = var.enable_api_gateway
}

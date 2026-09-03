output "endpoint_name" {
  value = module.endpoint.endpoint_name
}

output "endpoint_arn" {
  value = module.endpoint.endpoint_arn
}

output "api_invoke_url" {
  value = module.api_gateway.invoke_url
}

output "sns_alerts_topic_arn" {
  value = module.sns.alerts_topic_arn
}

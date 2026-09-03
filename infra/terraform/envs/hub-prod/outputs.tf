output "prod_data_bucket_name" {
  value = module.storage.prod_data_bucket_name
}

output "sns_alerts_topic_arn" {
  value = module.sns.alerts_topic_arn
}

output "deploy_trigger_arn" {
  value = module.deploy_trigger.state_machine_arn
}

output "prod_pipeline_config" {
  value = module.credit_risk_pipeline_prod.pipeline_config
}

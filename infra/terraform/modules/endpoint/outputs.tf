output "endpoint_name" {
  value = aws_sagemaker_endpoint.this.name
}

output "endpoint_arn" {
  value = aws_sagemaker_endpoint.this.arn
}

output "endpoint_config_name" {
  value = aws_sagemaker_endpoint_configuration.this.name
}

output "model_name" {
  value = aws_sagemaker_model.this.name
}

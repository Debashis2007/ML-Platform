output "vpc_id" {
  value = var.vpc_id
}

output "subnet_ids" {
  value = var.subnet_ids
}

output "sagemaker_security_group_id" {
  value = aws_security_group.sagemaker.id
}

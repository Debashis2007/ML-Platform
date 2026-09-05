output "vpc_id" {
  value = var.vpc_id
}

output "subnet_ids" {
  value = var.subnet_ids
}

output "sagemaker_security_group_id" {
  value = aws_security_group.sagemaker.id
}

output "vpc_endpoint_ids" {
  value = var.enable_vpc_endpoints ? merge(
    { s3 = aws_vpc_endpoint.s3[0].id },
    { for k, ep in aws_vpc_endpoint.interface : k => ep.id }
  ) : {}
}

output "vpc_endpoints_security_group_id" {
  value = try(aws_security_group.vpc_endpoints[0].id, null)
}

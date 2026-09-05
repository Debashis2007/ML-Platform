output "key_arn" {
  value = aws_kms_key.platform.arn
}

output "key_id" {
  value = aws_kms_key.platform.key_id
}

output "alias_arn" {
  value = aws_kms_alias.platform.arn
}

output "alias_name" {
  value = aws_kms_alias.platform.name
}

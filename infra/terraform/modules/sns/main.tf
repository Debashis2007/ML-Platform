resource "aws_sns_topic" "alerts" {
  name              = "${var.name_prefix}-ml-alerts"
  kms_master_key_id = var.kms_key_arn
  tags              = var.tags
}

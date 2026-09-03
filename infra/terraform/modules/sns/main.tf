resource "aws_sns_topic" "alerts" {
  name = "${var.name_prefix}-ml-alerts"
  tags = var.tags
}

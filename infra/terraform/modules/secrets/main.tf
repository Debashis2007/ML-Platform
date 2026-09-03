resource "aws_secretsmanager_secret" "pipeline" {
  name        = "${var.name_prefix}/pipeline/config"
  description = var.description
  tags        = var.tags
}

resource "aws_secretsmanager_secret_version" "pipeline" {
  secret_id = aws_secretsmanager_secret.pipeline.id
  secret_string = jsonencode({
    note = "Populate with hub/spoke credentials and data source URIs"
  })
}

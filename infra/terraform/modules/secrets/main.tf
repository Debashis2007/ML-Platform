resource "aws_secretsmanager_secret" "pipeline" {
  name        = "${var.name_prefix}/pipeline/config"
  description = var.description
  kms_key_id  = var.kms_key_arn
  tags        = var.tags
}

resource "aws_secretsmanager_secret_version" "pipeline" {
  secret_id = aws_secretsmanager_secret.pipeline.id
  secret_string = jsonencode({
    note = "Populate with hub/spoke credentials and data source URIs"
  })
}

resource "aws_secretsmanager_secret" "github_dispatch" {
  count       = var.github_dispatch_token != "" ? 1 : 0
  name        = "${var.name_prefix}/github/dispatch-token"
  description = "GitHub token for repository_dispatch on model approval"
  kms_key_id  = var.kms_key_arn
  tags        = var.tags
}

resource "aws_secretsmanager_secret_version" "github_dispatch" {
  count         = length(aws_secretsmanager_secret.github_dispatch) > 0 ? 1 : 0
  secret_id     = aws_secretsmanager_secret.github_dispatch[0].id
  secret_string = var.github_dispatch_token
}

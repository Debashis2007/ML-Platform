resource "aws_sagemaker_model_package_group" "this" {
  model_package_group_name        = var.model_package_group_name
  model_package_group_description = var.description
  tags                            = var.tags
}

resource "aws_ram_resource_share" "model_package" {
  count                     = length(var.spoke_account_ids) > 0 ? 1 : 0
  name                      = "${var.model_package_group_name}-share"
  allow_external_principals = true
  tags                      = var.tags
}

resource "aws_ram_principal_association" "spokes" {
  for_each           = length(var.spoke_account_ids) > 0 ? toset(var.spoke_account_ids) : toset([])
  resource_share_arn = aws_ram_resource_share.model_package[0].arn
  principal          = each.value
}

resource "aws_ram_resource_association" "model_package" {
  count              = length(var.spoke_account_ids) > 0 ? 1 : 0
  resource_share_arn = aws_ram_resource_share.model_package[0].arn
  resource_arn       = aws_sagemaker_model_package_group.this.arn
}

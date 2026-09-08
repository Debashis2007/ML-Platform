locals {
  active_bus = {
    for bu, cfg in var.business_units :
    bu => cfg
    if cfg.model_package_arn != null && cfg.model_package_arn != ""
  }
}

module "endpoint" {
  source   = "../endpoint"
  for_each = local.active_bus

  name_prefix             = "${var.name_prefix}-${lower(each.key)}"
  model_package_arn       = each.value.model_package_arn
  endpoint_name           = each.value.endpoint_name
  inference_role_arn      = var.inference_role_arn
  subnet_ids              = var.subnet_ids
  security_group_ids      = var.security_group_ids
  instance_type           = each.value.instance_type
  instance_count          = each.value.instance_count
  enable_multi_az         = each.value.enable_multi_az
  enable_data_capture     = each.value.enable_data_capture
  data_capture_s3_uri     = "s3://${var.artifacts_bucket_name}/data-capture/${each.value.endpoint_name}"
  kms_key_id              = var.kms_key_arn
  tags = merge(var.tags, {
    BusinessUnit = each.key
    Plane        = var.enable_api_gateway ? "prod" : "nonprod"
  })
}

module "api_gateway" {
  source   = "../api_gateway"
  for_each = var.enable_api_gateway ? local.active_bus : {}

  name_prefix               = "${var.name_prefix}-${lower(each.key)}"
  endpoint_name             = module.endpoint[each.key].endpoint_name
  endpoint_arn              = module.endpoint[each.key].endpoint_arn
  lambda_zip_path           = var.lambda_zip_path
  lambda_source_hash        = var.lambda_source_hash
  invoke_endpoint_image_uri = var.invoke_endpoint_image_uri
  lambda_role_arn           = var.invoke_lambda_role_arn
  enable_iam_auth    = var.enable_iam_auth
  tags = merge(var.tags, {
    BusinessUnit = each.key
  })
}

module "waf" {
  source   = "../waf"
  for_each = var.enable_api_gateway && var.enable_waf ? local.active_bus : {}

  name_prefix   = "${var.name_prefix}-${lower(each.key)}"
  resource_arns = [module.api_gateway[each.key].stage_arn]
  tags = merge(var.tags, {
    BusinessUnit = each.key
  })
}

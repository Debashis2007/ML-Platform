# Governance (design v7): four DynamoDB tables, copy-in registration, approval capture.
#
#   ml_lifecycle     one record per candidate (tenant#model, PKG#sha256); state machine
#   ml_decision_log  append-only decisions (registrations, approvals, violations, promotions)
#   ml_identity      approver identities, roles and tenant scope (management API)
#   ml_locks         approval locks with TTL and fencing; never restored after DR
#
# Restore order after DR: identity, then decision log, then lifecycle; reconcile before
# writes resume. Locks are recreated empty.

data "aws_caller_identity" "current" {}

locals {
  tables = {
    lifecycle    = { name = "${var.name_prefix}-ml_lifecycle", range_key = "sk", ttl = false }
    decision_log = { name = "${var.name_prefix}-ml_decision_log", range_key = "sk", ttl = false }
    identity     = { name = "${var.name_prefix}-ml_identity", range_key = null, ttl = false }
    locks        = { name = "${var.name_prefix}-ml_locks", range_key = null, ttl = true }
  }
  capture_use_image         = var.capture_approval_image_uri != ""
  github_dispatch_use_image = var.github_dispatch_image_uri != ""
  model_package_filter = var.model_package_group_name != "" ? {
    ModelPackageGroupName = [var.model_package_group_name]
  } : {}
}

resource "aws_dynamodb_table" "this" {
  for_each = local.tables

  name                        = each.value.name
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "pk"
  range_key                   = each.value.range_key
  deletion_protection_enabled = var.deletion_protection
  stream_enabled              = true
  stream_view_type            = "NEW_AND_OLD_IMAGES"

  attribute {
    name = "pk"
    type = "S"
  }

  dynamic "attribute" {
    for_each = each.value.range_key != null ? [each.value.range_key] : []
    content {
      name = attribute.value
      type = "S"
    }
  }

  dynamic "ttl" {
    for_each = each.value.ttl ? [1] : []
    content {
      attribute_name = "expires_at"
      enabled        = true
    }
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  tags = merge(var.tags, { Name = each.value.name, Table = each.key })
}

# Pre-v7 single governance table, kept so existing records are not destroyed on upgrade.
resource "aws_dynamodb_table" "governance" {
  count        = var.retain_legacy_governance_table ? 1 : 0
  name         = "${var.name_prefix}-model-governance"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }

  tags = merge(var.tags, { Legacy = "true" })
}

moved {
  from = aws_dynamodb_table.governance
  to   = aws_dynamodb_table.governance[0]
}

# --- Hub event bus: BU accounts forward pipeline status events here (v7 BU training) ---

resource "aws_cloudwatch_event_bus" "hub" {
  name = "${var.name_prefix}-ml-hub"
  tags = var.tags
}

data "aws_iam_policy_document" "hub_bus" {
  count = length(var.spoke_account_ids) > 0 ? 1 : 0

  statement {
    sid       = "AllowSpokePutEvents"
    actions   = ["events:PutEvents"]
    resources = [aws_cloudwatch_event_bus.hub.arn]
    principals {
      type        = "AWS"
      identifiers = [for a in var.spoke_account_ids : "arn:aws:iam::${a}:root"]
    }
  }
}

resource "aws_cloudwatch_event_bus_policy" "hub" {
  count          = length(var.spoke_account_ids) > 0 ? 1 : 0
  event_bus_name = aws_cloudwatch_event_bus.hub.name
  policy         = data.aws_iam_policy_document.hub_bus[0].json
}

# --- Copy-in registration ---

module "register_candidate" {
  source = "../platform_function"

  function_name      = "${var.name_prefix}-register-candidate"
  description        = "Copy-in registration: checksum-verified copy, PendingManualApproval package"
  role_arn           = var.registration_lambda_role_arn
  image_uri          = var.register_candidate_image_uri
  source_dir         = "${path.module}/../../../../lambdas/register_candidate"
  timeout            = 300
  memory_size        = 512
  subnet_ids         = var.lambda_subnet_ids
  security_group_ids = var.lambda_security_group_ids
  alarm_actions      = var.alarm_actions
  environment = {
    LIFECYCLE_TABLE          = aws_dynamodb_table.this["lifecycle"].name
    DECISION_LOG_TABLE       = aws_dynamodb_table.this["decision_log"].name
    ARTEFACT_BUCKET          = var.artefact_bucket_name
    EVIDENCE_BUCKET          = var.evidence_bucket_name
    ALLOWED_SOURCE_ACCOUNTS  = join(",", distinct(concat([data.aws_caller_identity.current.account_id], var.training_account_ids)))
    CONTROL_PLANE_ACCOUNT_ID = data.aws_caller_identity.current.account_id
    SOURCE_READ_ROLE_NAME    = var.source_read_role_name
  }
  tags = var.tags
}

locals {
  pipeline_succeeded_pattern = jsonencode({
    source      = ["aws.sagemaker"]
    detail-type = ["SageMaker Model Building Pipeline Execution Status Change"]
    detail      = { currentPipelineExecutionStatus = ["Succeeded"] }
  })
  registration_buses = {
    default = "default"
    hub     = aws_cloudwatch_event_bus.hub.name
  }
}

resource "aws_cloudwatch_event_rule" "pipeline_succeeded" {
  for_each = local.registration_buses

  name           = "${var.name_prefix}-pipeline-succeeded-${each.key}"
  description    = "Training pipeline succeeded → copy-in registration"
  event_bus_name = each.value
  event_pattern  = local.pipeline_succeeded_pattern
  tags           = var.tags
}

resource "aws_cloudwatch_event_target" "register_candidate" {
  for_each = local.registration_buses

  rule           = aws_cloudwatch_event_rule.pipeline_succeeded[each.key].name
  event_bus_name = each.value
  target_id      = "RegisterCandidate"
  arn            = module.register_candidate.arn

  retry_policy {
    maximum_retry_attempts       = 8
    maximum_event_age_in_seconds = 3600
  }
}

resource "aws_lambda_permission" "register_candidate" {
  for_each = local.registration_buses

  statement_id  = "AllowEventBridge-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = module.register_candidate.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.pipeline_succeeded[each.key].arn
}

# --- Approval capture: decision log, violation detection, deploy signal ---

resource "aws_cloudwatch_event_rule" "model_package_state_change" {
  name        = "${var.name_prefix}-model-package-state"
  description = "Fires on SageMaker Model Package approval status changes"
  event_pattern = jsonencode({
    source      = ["aws.sagemaker"]
    detail-type = ["SageMaker Model Package State Change"]
    detail = merge(local.model_package_filter, {
      ModelApprovalStatus = ["Approved", "Rejected", "PendingManualApproval"]
    })
  })
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "capture_approval" {
  name              = "/aws/lambda/${var.name_prefix}-capture-approval"
  retention_in_days = 365
  tags              = var.tags
}

resource "aws_lambda_function" "capture_approval" {
  function_name = "${var.name_prefix}-capture-approval"
  role          = var.governance_lambda_role_arn
  timeout       = 30
  memory_size   = 256

  package_type = local.capture_use_image ? "Image" : "Zip"
  image_uri    = local.capture_use_image ? var.capture_approval_image_uri : null

  handler          = local.capture_use_image ? null : "handler.lambda_handler"
  runtime          = local.capture_use_image ? null : "python3.11"
  filename         = local.capture_use_image ? null : (var.lambda_source_dir != "" ? "${var.lambda_source_dir}/capture_approval.zip" : "${path.module}/build/capture_approval.zip")
  source_code_hash = local.capture_use_image ? null : (var.lambda_source_dir != "" ? filebase64sha256("${var.lambda_source_dir}/capture_approval.zip") : filebase64sha256("${path.module}/build/capture_approval.zip"))

  environment {
    variables = {
      LIFECYCLE_TABLE         = aws_dynamodb_table.this["lifecycle"].name
      DECISION_LOG_TABLE      = aws_dynamodb_table.this["decision_log"].name
      DEPLOY_PARAMETER_PREFIX = var.deploy_parameter_prefix != "" ? var.deploy_parameter_prefix : "/${var.name_prefix}/deploy"
    }
  }

  depends_on = [aws_cloudwatch_log_group.capture_approval]
  tags       = var.tags
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.model_package_state_change.name
  target_id = "CaptureApproval"
  arn       = aws_lambda_function.capture_approval.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.capture_approval.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.model_package_state_change.arn
}

resource "aws_cloudwatch_metric_alarm" "governance_lambda_errors" {
  alarm_name          = "${var.name_prefix}-governance-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = var.alarm_actions
  dimensions = {
    FunctionName = aws_lambda_function.capture_approval.function_name
  }
  tags = var.tags
}

resource "aws_cloudwatch_event_rule" "approval_violation" {
  name        = "${var.name_prefix}-approval-violation"
  description = "A package was approved outside the management API"
  event_pattern = jsonencode({
    source      = ["ml.platform.governance"]
    detail-type = ["Model Approval Violation"]
  })
  tags = var.tags
}

resource "aws_cloudwatch_event_target" "approval_violation_sns" {
  count = var.violation_topic_arn != "" ? 1 : 0
  rule  = aws_cloudwatch_event_rule.approval_violation.name
  arn   = var.violation_topic_arn
}

# --- Auto-deploy: Model Approved → GitHub repository_dispatch ---

resource "aws_cloudwatch_event_rule" "model_approved_deploy" {
  count       = var.enable_auto_deploy ? 1 : 0
  name        = "${var.name_prefix}-model-approved-deploy"
  description = "Triggers GitHub release workflow on Model Approved"
  event_pattern = jsonencode({
    source      = ["ml.platform.governance"]
    detail-type = ["Model Approved"]
  })
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "github_dispatch" {
  count             = var.enable_auto_deploy ? 1 : 0
  name              = "/aws/lambda/${var.name_prefix}-github-dispatch"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_lambda_function" "github_dispatch" {
  count         = var.enable_auto_deploy ? 1 : 0
  function_name = "${var.name_prefix}-github-dispatch"
  role          = var.github_dispatch_lambda_role_arn
  timeout       = 30
  memory_size   = 256

  package_type = local.github_dispatch_use_image ? "Image" : "Zip"
  image_uri    = local.github_dispatch_use_image ? var.github_dispatch_image_uri : null

  handler          = local.github_dispatch_use_image ? null : "handler.lambda_handler"
  runtime          = local.github_dispatch_use_image ? null : "python3.11"
  filename         = local.github_dispatch_use_image ? null : "${var.lambda_source_dir}/github_dispatch.zip"
  source_code_hash = local.github_dispatch_use_image ? null : filebase64sha256("${var.lambda_source_dir}/github_dispatch.zip")

  environment {
    variables = {
      GITHUB_OWNER            = var.github_owner
      GITHUB_REPO             = var.github_repo
      GITHUB_TOKEN_SECRET_ARN = var.github_token_secret_arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.github_dispatch]
  tags       = var.tags
}

resource "aws_cloudwatch_event_target" "github_dispatch" {
  count     = var.enable_auto_deploy ? 1 : 0
  rule      = aws_cloudwatch_event_rule.model_approved_deploy[0].name
  target_id = "GitHubDispatch"
  arn       = aws_lambda_function.github_dispatch[0].arn
}

resource "aws_lambda_permission" "github_dispatch_events" {
  count         = var.enable_auto_deploy ? 1 : 0
  statement_id  = "AllowEventBridgeGitHubDispatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_dispatch[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.model_approved_deploy[0].arn
}

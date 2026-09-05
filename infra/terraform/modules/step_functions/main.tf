data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_sfn_state_machine" "pipeline_trigger" {
  name     = "${var.name_prefix}-${var.pipeline_name}-trigger"
  role_arn = var.sfn_role_arn
  tags     = var.tags

  definition = jsonencode({
    Comment = "Trigger SageMaker pipeline (DEV pipeline trigger / PROD deploy trigger)"
    StartAt = "StartPipeline"
    States = {
      StartPipeline = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:sagemaker:startPipelineExecution"
        Parameters = {
          PipelineName                 = var.pipeline_name
          PipelineExecutionDisplayName = "$$.Execution.Name"
        }
        End = true
      }
    }
  })
}

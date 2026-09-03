resource "aws_iam_role" "sfn" {
  name = "${var.name_prefix}-pipeline-trigger"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "sfn_sagemaker" {
  name = "${var.name_prefix}-sfn-sagemaker"
  role = aws_iam_role.sfn.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["sagemaker:StartPipelineExecution", "sagemaker:DescribePipeline"]
      Resource = "*"
    }]
  })
}

resource "aws_sfn_state_machine" "pipeline_trigger" {
  name     = "${var.name_prefix}-${var.pipeline_name}-trigger"
  role_arn = aws_iam_role.sfn.arn
  tags     = var.tags

  definition = jsonencode({
    Comment = "Trigger SageMaker pipeline (LLD: DEV Trigger Pipeline / PROD Trigger Deployment)"
    StartAt = "StartPipeline"
    States = {
      StartPipeline = {
        Type     = "Task"
        Resource = "arn:aws:states:::aws-sdk:sagemaker:startPipelineExecution"
        Parameters = {
          PipelineName                  = var.pipeline_name
          PipelineExecutionDisplayName  = "$$.Execution.Name"
        }
        End = true
      }
    }
  })
}

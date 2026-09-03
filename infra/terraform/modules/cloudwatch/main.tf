resource "aws_cloudwatch_log_group" "sagemaker" {
  name              = "/aws/sagemaker/${var.name_prefix}"
  retention_in_days = 30
  tags              = var.tags
}

resource "aws_cloudwatch_dashboard" "platform" {
  dashboard_name = "${var.name_prefix}-ml-platform"

  dashboard_body = jsonencode({
    widgets = concat(
      var.endpoint_name != "" ? [{
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "Endpoint ${var.endpoint_name}"
          region = data.aws_region.current.name
          metrics = [
            ["AWS/SageMaker", "ModelLatency", "EndpointName", var.endpoint_name, "VariantName", "AllTraffic"],
            [".", "Invocation4XXErrors", ".", ".", ".", "."],
            [".", "Invocation5XXErrors", ".", ".", ".", "."]
          ]
        }
      }] : [],
      [for i, pname in var.pipeline_names : {
        type   = "log"
        x      = 0
        y      = 6 + (i * 6)
        width  = 24
        height = 6
        properties = {
          title  = "Pipeline ${pname}"
          region = data.aws_region.current.name
          query  = "SOURCE '/aws/sagemaker/pipelines/${pname}' | fields @timestamp, @message | sort @timestamp desc | limit 20"
        }
      }]
    )
  })
}

data "aws_region" "current" {}

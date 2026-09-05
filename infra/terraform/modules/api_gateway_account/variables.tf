variable "cloudwatch_role_arn" {
  type        = string
  description = "Client-managed IAM role ARN trusted by apigateway.amazonaws.com (AmazonAPIGatewayPushToCloudWatchLogs)."
}

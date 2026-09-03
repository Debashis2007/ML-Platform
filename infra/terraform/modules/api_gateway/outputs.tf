output "api_endpoint" {
  value = aws_apigatewayv2_api.http.api_endpoint
}

output "invoke_url" {
  value = "${aws_apigatewayv2_api.http.api_endpoint}/invocations"
}

output "lambda_arn" {
  value = aws_lambda_function.invoke.arn
}

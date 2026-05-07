output "api_url" {
  description = "Monitoring API Gateway invoke URL"
  value       = aws_api_gateway_stage.monitoring.invoke_url
}

output "lambda_function_name" {
  description = "Monitoring API Lambda function name"
  value       = aws_lambda_function.monitoring_api.function_name
}

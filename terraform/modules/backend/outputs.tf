output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = "${aws_api_gateway_stage.prod.invoke_url}"
}

output "lambda_function_name" {
  description = "Main Lambda function name"
  value       = aws_lambda_function.chat.function_name
}

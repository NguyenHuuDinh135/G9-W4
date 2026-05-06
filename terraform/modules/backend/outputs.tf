output "api_gateway_url" {
  value = aws_api_gateway_stage.prod.invoke_url
}

output "lambda_function_name" {
  value = aws_lambda_function.chat.function_name
}

output "agent_id" {
  value = aws_bedrockagent_agent.main.agent_id
}

output "agent_alias_id" {
  value = aws_bedrockagent_agent_alias.prod.agent_alias_id
}

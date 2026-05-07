output "frontend_cloudfront_url" {
  description = "CloudFront URL for the chat frontend"
  value       = module.frontend.cloudfront_url
}

output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = module.backend.api_gateway_url
}

output "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID"
  value       = module.ai_engine.knowledge_base_id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = module.backend.lambda_function_name
}

output "kb_docs_bucket" {
  description = "S3 bucket for knowledge base documents"
  value       = module.ai_engine.kb_docs_bucket
}

output "opensearch_collection_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = module.ai_engine.opensearch_collection_endpoint
}

output "monitoring_api_url" {
  description = "Monitoring API Gateway URL"
  value       = module.monitoring_api.api_url
}

output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.main.id
}

output "kb_docs_bucket" {
  value = aws_s3_bucket.kb_docs.bucket
}

output "opensearch_collection_endpoint" {
  value = aws_opensearchserverless_collection.kb.collection_endpoint
}

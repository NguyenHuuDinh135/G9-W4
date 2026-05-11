variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "geekbrain"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "llm_model_id" {
  description = "Bedrock LLM model ID"
  type        = string
  default     = "deepseek.v3.2"
}

variable "embedding_model_id" {
  description = "Bedrock embedding model ARN"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "retrieval_k" {
  description = "Number of chunks to retrieve from KB"
  type        = number
  default     = 10
}

variable "kb_docs_path" {
  description = "Local path to knowledge base markdown files"
  type        = string
  default     = "../data_package/knowledge_base"
}

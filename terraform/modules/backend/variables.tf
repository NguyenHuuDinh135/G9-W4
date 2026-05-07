variable "project" {
  type = string
}

variable "tags" {
  type = map(string)
}

variable "region" {
  type = string
}

variable "account_id" {
  type = string
}

variable "llm_model_id" {
  type = string
}

variable "knowledge_base_id" {
  type = string
}

variable "retrieval_k" {
  type    = number
  default = 10
}

variable "monitoring_api_url" {
  description = "Monitoring API Gateway URL for action group tool calls"
  type        = string
}

variable "private_subnet_ids" {
  type    = list(string)
  default = []
}

variable "lambda_sg_id" {
  type    = string
  default = ""
}

variable "db_host" {
  type    = string
  default = ""
}

variable "db_name" {
  type    = string
  default = ""
}

variable "db_user" {
  type    = string
  default = ""
}

variable "db_password" {
  type    = string
  default = ""
}


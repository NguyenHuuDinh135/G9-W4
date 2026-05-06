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

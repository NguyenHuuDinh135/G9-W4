variable "project" {
  type = string
}

variable "tags" {
  description = "Tags for the resources"
  type        = map(string)
}

variable "vpc_endpoint_id" {
  description = "The ID of the VPC Interface Endpoint for API Gateway"
  type        = string
}

variable "project" {
  type = string
}

variable "tags" {
  type = map(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "rds_sg_id" {
  type = string
}

variable "lambda_sg_id" {
  type = string
}


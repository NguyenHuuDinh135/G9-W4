variable "function_name" {
  description = "Name of the Cost Guard Lambda function."
  type        = string
  default     = "w6-cost-guard"
}

variable "role_name" {
  description = "Name of the IAM role assumed by the Cost Guard Lambda."
  type        = string
  default     = "w6-cost-guard-lambda-role"
}

variable "policy_name" {
  description = "Name of the least-privilege IAM policy for the Cost Guard Lambda."
  type        = string
  default     = "w6-cost-guard-lambda-policy"
}

variable "schedule_rule_name" {
  description = "Name of the EventBridge schedule rule."
  type        = string
  default     = "w6-cost-guard-daily"
}

variable "schedule_expression" {
  description = "EventBridge schedule expression. Default runs daily at 18:00 UTC. Use rate(5 minutes) for demo if needed."
  type        = string
  default     = "cron(0 18 * * ? *)"
}

variable "budget_name" {
  description = "Name of the daily AWS Budget that drives the SNS -> Lambda cost-control path."
  type        = string
  default     = "w6-cost-guard-daily-150-usd"
}

variable "budget_limit_usd" {
  description = "Daily AWS Budget limit in USD for the W6 hard cost cap path."
  type        = string
  default     = "150"
}

variable "budget_alert_threshold_percent" {
  description = "Budget notification threshold percentage. 100 means notify when actual daily spend is greater than the configured USD limit."
  type        = number
  default     = 100
}

variable "budget_sns_topic_name" {
  description = "SNS topic name for AWS Budgets notifications that invoke the Cost Guard Lambda."
  type        = string
  default     = "w6-cost-guard-budget-alerts"
}

variable "dry_run" {
  description = "When true, Lambda reports resources that would be stopped without calling StopInstances/StopDBInstance. Set false for acceptance demo."
  type        = bool
  default     = false
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout in seconds."
  type        = number
  default     = 60
}

variable "lambda_memory_mb" {
  description = "Lambda memory size in MB."
  type        = number
  default     = 128
}

variable "log_level" {
  description = "Python logger level."
  type        = string
  default     = "INFO"
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention for the Cost Guard Lambda log group."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Tags applied to Cost Guard resources."
  type        = map(string)
  default = {
    Application = "xbrain-w6"
    Environment = "dev"
    Owner       = "group"
    CostCenter  = "xbrain"
  }
}

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "archive_file" "cost_guard_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_function.py"
  output_path = "${path.module}/build/cost_guard_lambda.zip"
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "cost_guard_lambda" {
  name               = var.role_name
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "cost_guard" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

data "aws_iam_policy_document" "cost_guard_permissions" {
  statement {
    sid    = "WriteLambdaLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "${aws_cloudwatch_log_group.cost_guard.arn}:*"
    ]
  }

  # Describe/List actions must use resource "*" because AWS does not support
  # resource-level constraints for these inventory APIs.
  statement {
    sid    = "DescribeCostGuardTargets"
    effect = "Allow"
    actions = [
      "ec2:DescribeInstances",
      "rds:DescribeDBInstances",
      "rds:ListTagsForResource"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "StopUntaggedEc2Instances"
    effect = "Allow"
    actions = [
      "ec2:StopInstances"
    ]
    resources = [
      "arn:aws:ec2:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:instance/*"
    ]
  }

  statement {
    sid    = "StopUntaggedRdsInstances"
    effect = "Allow"
    actions = [
      "rds:StopDBInstance"
    ]
    resources = [
      "arn:aws:rds:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:db:*"
    ]
  }
}

resource "aws_sns_topic" "cost_guard_budget" {
  name = var.budget_sns_topic_name

  tags = var.tags
}

data "aws_iam_policy_document" "cost_guard_budget_topic" {
  statement {
    sid    = "AllowBudgetsToPublish"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }

    actions = ["SNS:Publish"]

    resources = [aws_sns_topic.cost_guard_budget.arn]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_sns_topic_policy" "cost_guard_budget" {
  arn    = aws_sns_topic.cost_guard_budget.arn
  policy = data.aws_iam_policy_document.cost_guard_budget_topic.json
}

resource "aws_iam_policy" "cost_guard" {
  name        = var.policy_name
  description = "Least-privilege permissions for W6 Cost Guard Lambda: describe/list targets and stop EC2/RDS."
  policy      = data.aws_iam_policy_document.cost_guard_permissions.json

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "cost_guard" {
  role       = aws_iam_role.cost_guard_lambda.name
  policy_arn = aws_iam_policy.cost_guard.arn
}

resource "aws_lambda_function" "cost_guard" {
  function_name    = var.function_name
  description      = "W6 Automated Cost Guard: stops EC2/RDS resources missing keep=true or Environment=dev."
  role             = aws_iam_role.cost_guard_lambda.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = var.lambda_timeout_seconds
  memory_size      = var.lambda_memory_mb
  filename         = data.archive_file.cost_guard_zip.output_path
  source_code_hash = data.archive_file.cost_guard_zip.output_base64sha256

  environment {
    variables = {
      DRY_RUN        = tostring(var.dry_run)
      KEEP_TAG_KEY   = "keep"
      KEEP_TAG_VALUE = "true"
      ENV_TAG_KEY    = "Environment"
      ENV_TAG_VALUE  = "dev"
      LOG_LEVEL      = var.log_level
    }
  }

  tags = var.tags

  depends_on = [aws_iam_role_policy_attachment.cost_guard]
}

resource "aws_cloudwatch_event_rule" "cost_guard_schedule" {
  name                = var.schedule_rule_name
  description         = "Scheduled trigger for W6 Cost Guard Lambda."
  schedule_expression = var.schedule_expression

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "cost_guard_lambda" {
  rule      = aws_cloudwatch_event_rule.cost_guard_schedule.name
  target_id = "cost-guard-lambda"
  arn       = aws_lambda_function.cost_guard.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_guard.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cost_guard_schedule.arn
}

resource "aws_lambda_permission" "allow_budget_sns" {
  statement_id  = "AllowExecutionFromBudgetSns"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_guard.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.cost_guard_budget.arn
}

resource "aws_sns_topic_subscription" "cost_guard_lambda" {
  topic_arn = aws_sns_topic.cost_guard_budget.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.cost_guard.arn

  depends_on = [aws_lambda_permission.allow_budget_sns]
}

resource "aws_budgets_budget" "daily_cost_guard" {
  name         = var.budget_name
  budget_type  = "COST"
  limit_amount = var.budget_limit_usd
  limit_unit   = "USD"
  time_unit    = "DAILY"

  notification {
    comparison_operator       = "GREATER_THAN"
    threshold                 = var.budget_alert_threshold_percent
    threshold_type            = "PERCENTAGE"
    notification_type         = "ACTUAL"
    subscriber_sns_topic_arns = [aws_sns_topic.cost_guard_budget.arn]
  }

  depends_on = [
    aws_sns_topic_policy.cost_guard_budget,
    aws_sns_topic_subscription.cost_guard_lambda
  ]
}

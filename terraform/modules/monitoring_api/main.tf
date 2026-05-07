# ═══════════════════════════════════════
# Monitoring API — Lambda + API Gateway
# Deploys monitoring_api.py (FastAPI) behind API Gateway
# ═══════════════════════════════════════

# --- IAM Role ---
resource "aws_iam_role" "monitoring_lambda" {
  name = "${var.project}-monitoring-api-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "monitoring_lambda_logs" {
  role       = aws_iam_role.monitoring_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- Build the deployment package ---
resource "null_resource" "monitoring_build" {
  triggers = {
    source_hash = md5(join(",", [
      filemd5("../monitoring_lambda/monitoring_api.py"),
      filemd5("../monitoring_lambda/handler.py"),
      filemd5("../monitoring_lambda/requirements.txt"),
    ]))
  }

  provisioner "local-exec" {
    command     = "python build.py"
    working_dir = "../monitoring_lambda"
  }
}

data "archive_file" "monitoring_lambda" {
  type        = "zip"
  source_dir  = "../monitoring_lambda/.build"
  output_path = "${path.module}/.build/monitoring_lambda.zip"
  depends_on  = [null_resource.monitoring_build]
}

# --- Lambda Function ---
resource "aws_lambda_function" "monitoring_api" {
  function_name    = "${var.project}-monitoring-api"
  role             = aws_iam_role.monitoring_lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 256
  filename         = data.archive_file.monitoring_lambda.output_path
  source_code_hash = data.archive_file.monitoring_lambda.output_base64sha256
  tags             = var.tags
}

resource "aws_lambda_permission" "monitoring_apigw" {
  statement_id  = "AllowMonitoringAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.monitoring_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.monitoring.execution_arn}/*/*"
}

# ═══════════════════════════════════════
# API Gateway — proxy all routes to Lambda
# ═══════════════════════════════════════

resource "aws_api_gateway_rest_api" "monitoring" {
  name        = "${var.project}-monitoring-api"
  description = "GeekBrain Monitoring API — live service status, metrics, incidents"

  endpoint_configuration {
    types            = ["PRIVATE"]
    vpc_endpoint_ids = [var.vpc_endpoint_id]
  }

  tags = var.tags
}

resource "aws_api_gateway_rest_api_policy" "monitoring" {
  rest_api_id = aws_api_gateway_rest_api.monitoring.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = "*"
        Action    = "execute-api:Invoke"
        Resource  = "${aws_api_gateway_rest_api.monitoring.execution_arn}/*"
      },
      {
        Effect    = "Deny"
        Principal = "*"
        Action    = "execute-api:Invoke"
        Resource  = "${aws_api_gateway_rest_api.monitoring.execution_arn}/*"
        Condition = {
          StringNotEquals = {
            "aws:SourceVpce" = var.vpc_endpoint_id
          }
        }
      }
    ]
  })
}

# --- Root resource GET (/) ---
resource "aws_api_gateway_method" "root_get" {
  rest_api_id   = aws_api_gateway_rest_api.monitoring.id
  resource_id   = aws_api_gateway_rest_api.monitoring.root_resource_id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "root_get" {
  rest_api_id             = aws_api_gateway_rest_api.monitoring.id
  resource_id             = aws_api_gateway_rest_api.monitoring.root_resource_id
  http_method             = aws_api_gateway_method.root_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.monitoring_api.invoke_arn
}

# --- Proxy resource {proxy+} for all sub-paths ---
resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.monitoring.id
  parent_id   = aws_api_gateway_rest_api.monitoring.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy_get" {
  rest_api_id   = aws_api_gateway_rest_api.monitoring.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "proxy_get" {
  rest_api_id             = aws_api_gateway_rest_api.monitoring.id
  resource_id             = aws_api_gateway_resource.proxy.id
  http_method             = aws_api_gateway_method.proxy_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.monitoring_api.invoke_arn
}

# --- Deploy ---
resource "aws_api_gateway_deployment" "monitoring" {
  rest_api_id = aws_api_gateway_rest_api.monitoring.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_method.root_get.id,
      aws_api_gateway_integration.root_get.id,
      aws_api_gateway_method.proxy_get.id,
      aws_api_gateway_integration.proxy_get.id,
      aws_api_gateway_rest_api_policy.monitoring.policy,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "monitoring" {
  deployment_id = aws_api_gateway_deployment.monitoring.id
  rest_api_id   = aws_api_gateway_rest_api.monitoring.id
  stage_name    = "prod"
  tags          = var.tags
}

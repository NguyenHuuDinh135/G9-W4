# ═══════════════════════════════════════
# Seed Data Automation
# ═══════════════════════════════════════

resource "null_resource" "seed_build" {
  triggers = {
    # Trigger on any changes to the seed code or data
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "python build.py"
    working_dir = "${path.root}/../seed_lambda"
  }
}

data "archive_file" "seed_lambda" {
  type        = "zip"
  source_dir  = "${path.root}/../seed_lambda/.build"
  output_path = "${path.module}/.build/seed_lambda.zip"
  depends_on  = [null_resource.seed_build]
}

resource "aws_iam_role" "seed_lambda" {
  name = "${var.project}-seed-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "seed_vpc_execution" {
  role       = aws_iam_role.seed_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_function" "seed_lambda" {
  filename         = data.archive_file.seed_lambda.output_path
  function_name    = "${var.project}-seed-db"
  role             = aws_iam_role.seed_lambda.arn
  handler          = "handler.handler"
  source_code_hash = data.archive_file.seed_lambda.output_base64sha256
  runtime          = "python3.12"
  timeout          = 120
  memory_size      = 256

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_sg_id]
  }

  environment {
    variables = {
      DB_HOST     = aws_db_instance.postgres.address
      DB_NAME     = aws_db_instance.postgres.db_name
      DB_USER     = aws_db_instance.postgres.username
      DB_PASSWORD = aws_db_instance.postgres.password
    }
  }

  tags = var.tags
  depends_on = [aws_db_instance.postgres]
}

# Invoke the lambda automatically after creation
resource "null_resource" "invoke_seed" {
  triggers = {
    # Rerun if db host changes, or if code changes
    db_host = aws_db_instance.postgres.address
    lambda_hash = aws_lambda_function.seed_lambda.source_code_hash
  }

  provisioner "local-exec" {
    command = "aws lambda invoke --function-name ${aws_lambda_function.seed_lambda.function_name} --region us-east-1 response.json"
  }
  
  depends_on = [aws_lambda_function.seed_lambda]
}

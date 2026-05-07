# ═══════════════════════════════════════
# VPC and Subnets
# ═══════════════════════════════════════

# ═══════════════════════════════════════
# VPC and Subnets (Using Default VPC due to limit)
# ═══════════════════════════════════════

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# ═══════════════════════════════════════
# Security Groups
# ═══════════════════════════════════════

# Security Group for Lambda functions (Action Group & Seed)
resource "aws_security_group" "lambda" {
  name        = "${var.project}-lambda-sg"
  description = "Security group for Lambda functions"
  vpc_id      = data.aws_vpc.default.id

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project}-lambda-sg" })
}

# Security Group for RDS PostgreSQL
resource "aws_security_group" "rds" {
  name        = "${var.project}-rds-sg"
  description = "Security group for RDS instance"
  vpc_id      = data.aws_vpc.default.id

  # Allow inbound from Lambda SG only on 5432
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project}-rds-sg" })
}

# Security Group for VPC Interface Endpoint
resource "aws_security_group" "endpoint" {
  name        = "${var.project}-endpoint-sg"
  description = "Security group for VPC Interface Endpoints"
  vpc_id      = data.aws_vpc.default.id

  # Allow inbound HTTPS from Lambda SG
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project}-endpoint-sg" })
}

# ═══════════════════════════════════════
# VPC Interface Endpoint for API Gateway
# ═══════════════════════════════════════
data "aws_region" "current" {}

resource "aws_vpc_endpoint" "apigw" {
  vpc_id              = data.aws_vpc.default.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.execute-api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.endpoint.id]
  private_dns_enabled = true # Essential: routes *.execute-api calls internally

  tags = merge(var.tags, { Name = "${var.project}-apigw-endpoint" })
}

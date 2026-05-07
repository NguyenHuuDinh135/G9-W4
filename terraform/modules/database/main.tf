# ═══════════════════════════════════════
# RDS PostgreSQL Instance
# ═══════════════════════════════════════

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-db-subnet-group"
  subnet_ids = var.private_subnet_ids
  tags       = merge(var.tags, { Name = "${var.project}-db-subnet-group" })
}

resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_db_instance" "postgres" {
  identifier           = "${var.project}-postgres"
  engine               = "postgres"
  engine_version       = "15"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_type         = "gp2"
  db_name              = "geekbrain"
  username             = "postgres"
  password             = random_password.db_password.result
  
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.rds_sg_id]
  
  publicly_accessible    = false
  skip_final_snapshot    = true
  apply_immediately      = true
  
  tags = merge(var.tags, { Name = "${var.project}-postgres" })
}

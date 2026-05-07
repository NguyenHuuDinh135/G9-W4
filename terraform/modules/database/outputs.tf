output "db_host" {
  value = aws_db_instance.postgres.address
}

output "db_name" {
  value = aws_db_instance.postgres.db_name
}

output "db_user" {
  value = aws_db_instance.postgres.username
}

output "db_password" {
  value     = aws_db_instance.postgres.password
  sensitive = true
}

output "db_port" {
  value = aws_db_instance.postgres.port
}

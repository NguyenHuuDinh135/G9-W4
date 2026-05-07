output "vpc_id" {
  value = data.aws_vpc.default.id
}

output "private_subnet_ids" {
  value = slice(data.aws_subnets.default.ids, 0, 2)
}

output "lambda_sg_id" {
  value = aws_security_group.lambda.id
}

output "rds_sg_id" {
  value = aws_security_group.rds.id
}

output "vpc_endpoint_id" {
  value = aws_vpc_endpoint.apigw.id
}

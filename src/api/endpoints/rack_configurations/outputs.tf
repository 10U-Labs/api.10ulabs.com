output "lambda_function_arn" {
  description = "ARN of the rack configurations Lambda."
  value       = aws_lambda_function.handler.arn
}

output "lambda_function_name" {
  description = "Name of the rack configurations Lambda."
  value       = aws_lambda_function.handler.function_name
}

output "table_name" {
  description = "The table the configurations are stored in."
  value       = aws_dynamodb_table.configurations.name
}

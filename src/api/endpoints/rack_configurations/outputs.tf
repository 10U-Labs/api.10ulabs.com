output "lambda_function_arns" {
  description = "ARN of each verb's Lambda, by verb."
  value       = { for verb, function in aws_lambda_function.verb : verb => function.arn }
}

output "lambda_function_names" {
  description = "Name of each verb's Lambda, by verb."
  value       = { for verb, function in aws_lambda_function.verb : verb => function.function_name }
}

output "table_name" {
  description = "The table the configurations are stored in."
  value       = aws_dynamodb_table.configurations.name
}

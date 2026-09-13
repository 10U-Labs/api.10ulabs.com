output "lambda_function_arn" {
  description = "ARN of the sessions Lambda."
  value       = aws_lambda_function.handler.arn
}

output "lambda_function_name" {
  description = "Name of the sessions Lambda."
  value       = aws_lambda_function.handler.function_name
}

output "table_name" {
  description = "The table the events are recorded in."
  value       = aws_dynamodb_table.events.name
}

output "analytics_bucket" {
  description = "The bucket the daily export lands in."
  value       = aws_s3_bucket.analytics.bucket
}

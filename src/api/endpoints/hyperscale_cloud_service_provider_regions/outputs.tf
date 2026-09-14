output "lambda_function_arn" {
  description = "ARN of the hyperscale cloud service provider regions Lambda."
  value       = aws_lambda_function.handler.arn
}

output "lambda_function_name" {
  description = "Name of the hyperscale cloud service provider regions Lambda."
  value       = aws_lambda_function.handler.function_name
}

output "lambda_function_arn" {
  description = "ARN of the wan syntheses Lambda."
  value       = aws_lambda_function.handler.arn
}

output "lambda_function_name" {
  description = "Name of the wan syntheses Lambda."
  value       = aws_lambda_function.handler.function_name
}

output "writer_function_name" {
  description = "Name of the Lambda that creates and deletes wan syntheses."
  value       = aws_lambda_function.writer.function_name
}

output "synthesizer_function_name" {
  description = "Name of the Lambda that computes a wan synthesis."
  value       = aws_lambda_function.synthesizer.function_name
}

output "failure_handler_function_name" {
  description = "Name of the Lambda that marks a killed synthesis timeout."
  value       = aws_lambda_function.failure_handler.function_name
}

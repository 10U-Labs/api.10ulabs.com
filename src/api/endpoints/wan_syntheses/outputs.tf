output "lambda_function_arns" {
  description = "ARN of each verb's Lambda, by verb."
  value       = { for verb, function in aws_lambda_function.verb : verb => function.arn }
}

output "lambda_function_names" {
  description = "Name of each verb's Lambda, by verb."
  value       = { for verb, function in aws_lambda_function.verb : verb => function.function_name }
}

output "synthesizer_function_name" {
  description = "Name of the Lambda that computes a wan synthesis."
  value       = aws_lambda_function.synthesizer.function_name
}

output "failure_handler_function_name" {
  description = "Name of the Lambda that marks a killed synthesis timeout."
  value       = aws_lambda_function.failure_handler.function_name
}

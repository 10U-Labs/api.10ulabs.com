data "archive_file" "catchall" {
  type        = "zip"
  source_file = "${path.module}/lambda/catchall/handler.py"
  output_path = "${path.module}/.terraform/lambda_packages/catchall.zip"
}

resource "aws_lambda_function" "catchall" {
  filename         = data.archive_file.catchall.output_path
  function_name    = local.names.catchall
  role             = aws_iam_role.catchall.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.catchall.output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 128
  description      = "Catch-all: answer 404 for any route no other handler serves."

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT = "true"
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.catchall.name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.catchall.id]
  }
}

resource "aws_cloudwatch_log_group" "catchall" {
  name              = "/aws/lambda/${local.names.catchall}"
  retention_in_days = 7
}

resource "aws_lambda_permission" "catchall" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.catchall.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*"
}

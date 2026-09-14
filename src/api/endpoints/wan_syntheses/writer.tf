locals {
  writer_name = module.common.lambda_handler_names.wan_syntheses_writer
  writer_role = "${local.writer_name}-lambda"
}

data "archive_file" "writer" {
  type = "zip"
  source {
    content  = file("${path.module}/writer/handler.py")
    filename = "handler.py"
  }
  source {
    content  = file("${path.module}/../../../../lib/python/lambda_http/__init__.py")
    filename = "lambda_http.py"
  }
  source {
    content  = file("${path.module}/../../../../lib/python/store/__init__.py")
    filename = "store.py"
  }
  output_path = "${path.module}/.terraform/lambda_packages/writer.zip"
}

resource "aws_lambda_function" "writer" {
  filename         = data.archive_file.writer.output_path
  function_name    = local.writer_name
  role             = aws_iam_role.writer.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.writer.output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 256
  description      = "WAN syntheses writer: creates a synthesis from a run's inputs, writing its record and list items under the next id and starting the synthesizer on it, and deletes a finished synthesis with everything under it."

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT = "true"
      STORE_TABLE           = data.terraform_remote_state.storage.outputs.table_name
      SYNTHESIZER           = aws_lambda_function.synthesizer.function_name
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.writer.name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.writer.id]
  }
}

resource "aws_cloudwatch_log_group" "writer" {
  name              = "/aws/lambda/${local.writer_name}"
  retention_in_days = 7
}

resource "aws_lambda_permission" "writer_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.writer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${module.common.aws_region}:${module.common.aws_account_id}:${data.terraform_remote_state.routing.outputs.api_gateway_id}/*"
}

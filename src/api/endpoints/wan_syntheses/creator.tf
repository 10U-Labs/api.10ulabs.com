locals {
  creator_name = module.common.lambda_handler_names.wan_syntheses_post
  creator_role = "${local.creator_name}-lambda"
}

data "archive_file" "creator" {
  type = "zip"
  source {
    content  = file("${path.module}/post/handler.py")
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
  output_path = "${path.module}/.terraform/lambda_packages/creator.zip"
}

resource "aws_lambda_function" "creator" {
  filename         = data.archive_file.creator.output_path
  function_name    = local.creator_name
  role             = aws_iam_role.creator.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.creator.output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 256
  description      = "WAN syntheses creator: validates a run's inputs, writes its record and list items under the next id, and starts the synthesizer on it."

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT = "true"
      STORE_TABLE           = data.terraform_remote_state.storage.outputs.table_name
      SYNTHESIZER           = aws_lambda_function.synthesizer.function_name
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.creator.name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.creator.id]
  }
}

resource "aws_cloudwatch_log_group" "creator" {
  name              = "/aws/lambda/${local.creator_name}"
  retention_in_days = 7
}

resource "aws_lambda_permission" "creator_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.creator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${module.common.aws_region}:${module.common.aws_account_id}:${data.terraform_remote_state.routing.outputs.api_gateway_id}/*"
}

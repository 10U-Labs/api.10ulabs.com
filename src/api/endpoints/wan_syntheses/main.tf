module "common" {
  source = "../../../../lib/opentofu/common"
}

locals {
  function_name = module.common.lambda_handler_names.wan_syntheses
  role_name     = "${local.function_name}-lambda"
}

data "terraform_remote_state" "routing" {
  backend = "s3"

  config = {
    bucket = module.common.state_bucket
    key    = "api.10ulabs.com/src/api/common/routing/terraform.tfstate"
    region = module.common.aws_region
  }
}

data "terraform_remote_state" "storage" {
  backend = "s3"

  config = {
    bucket = module.common.state_bucket
    key    = "api.10ulabs.com/src/api/common/storage/terraform.tfstate"
    region = module.common.aws_region
  }
}

data "archive_file" "handler" {
  type = "zip"
  source {
    content  = file("${path.module}/lambda/handler.py")
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
  output_path = "${path.module}/.terraform/lambda_packages/handler.zip"
}

resource "aws_lambda_function" "handler" {
  filename         = data.archive_file.handler.output_path
  function_name    = local.function_name
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.handler.output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 128
  description      = "WAN syntheses endpoint: list the syntheses in the store, serve one by its id, list a WAN's PoPs or serve one by its id, and list a WAN's backbone and homing circuits."

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT = "true"
      STORE_TABLE           = data.terraform_remote_state.storage.outputs.table_name
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.handler.name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.lambda.id]
  }
}

resource "aws_cloudwatch_log_group" "handler" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 7
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${module.common.aws_region}:${module.common.aws_account_id}:${data.terraform_remote_state.routing.outputs.api_gateway_id}/*"
}

variable "authorized_accounts" {
  description = "The 10ulabs.com accounts authorized to use the protected routes, comma-separated, as the deploy passes them from the repository variable API_10ULABS_COM_AUTHORIZED_ACCOUNTS."
  type        = string

  validation {
    condition     = alltrue([for account in split(",", var.authorized_accounts) : endswith(trimspace(account), "@${module.common.domain_name}")])
    error_message = "Every authorized account is an address on the hosted domain."
  }
}

variable "api_key_rotation" {
  description = "The date the API key was last rotated, as the deploy passes it from the repository variable API_10ULABS_COM_API_KEY_ROTATION; a later date writes a fresh key. Rotate every 180 days, and at once on suspected compromise."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.api_key_rotation))
    error_message = "The rotation date is a calendar date, YYYY-MM-DD."
  }
}

locals {
  authorizer_name   = local.names.authorizer
  authorizer_role   = "${local.authorizer_name}-lambda"
  parameters_prefix = "/${module.common.api_name}"
}

resource "aws_ssm_parameter" "authorized_accounts" {
  name  = "${local.parameters_prefix}/authorized-accounts"
  type  = "StringList"
  value = var.authorized_accounts
}

ephemeral "random_password" "api_key" {
  length  = 48
  special = false
}

resource "aws_ssm_parameter" "api_key" {
  name             = "${local.parameters_prefix}/api-key"
  type             = "SecureString"
  value_wo         = ephemeral.random_password.api_key.result
  value_wo_version = tonumber(replace(var.api_key_rotation, "-", ""))
}

data "archive_file" "authorizer" {
  type = "zip"
  source {
    content  = file("${path.module}/lambda/authorizer/handler.py")
    filename = "handler.py"
  }
  source {
    content  = file("${path.module}/../../../../lib/python/lambda_http/__init__.py")
    filename = "lambda_http.py"
  }
  output_path = "${path.module}/.terraform/lambda_packages/authorizer.zip"
}

resource "aws_lambda_function" "authorizer" {
  filename         = data.archive_file.authorizer.output_path
  function_name    = local.authorizer_name
  role             = aws_iam_role.authorizer.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.authorizer.output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 128
  description      = "Authorizer: admit an authorized Google account on the hosted domain to every route, or the API key the workflows hold to the reads and the writes they make."

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT         = "true"
      GOOGLE_CLIENT_ID              = "846587722064-qjou8en4tk96n12ii3rgnpjshnbqovok.apps.googleusercontent.com"
      HOSTED_DOMAIN                 = module.common.domain_name
      API_KEY_PARAMETER             = aws_ssm_parameter.api_key.name
      AUTHORIZED_ACCOUNTS_PARAMETER = aws_ssm_parameter.authorized_accounts.name
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.authorizer.name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.authorizer.id]
  }
}

resource "aws_cloudwatch_log_group" "authorizer" {
  name              = "/aws/lambda/${local.authorizer_name}"
  retention_in_days = 7
}

resource "aws_lambda_permission" "authorizer" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/authorizers/*"
}

resource "aws_iam_role" "authorizer" {
  name = local.authorizer_role

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "authorizer_logs" {
  name = "Logs"
  role = aws_iam_role.authorizer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = ["${aws_cloudwatch_log_group.authorizer.arn}:*"]
    }]
  })
}

resource "aws_iam_role_policy" "authorizer_parameters" {
  name = "Parameters"
  role = aws_iam_role.authorizer.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter"]
      Resource = [aws_ssm_parameter.api_key.arn, aws_ssm_parameter.authorized_accounts.arn]
    }]
  })
}

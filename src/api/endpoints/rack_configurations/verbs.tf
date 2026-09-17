locals {
  verbs = {
    store_rack_configuration = {
      name        = module.common.lambda_handler_names.store_rack_configuration
      description = "Stores a rack configuration under its hash, invalidating the cached read of that hash the first time."
      actions     = ["dynamodb:PutItem"]
    }
    read_rack_configuration = {
      name        = module.common.lambda_handler_names.read_rack_configuration
      description = "Serves a rack configuration by its hash."
      actions     = ["dynamodb:GetItem"]
    }
  }
}

data "archive_file" "verb" {
  for_each = local.verbs

  type = "zip"
  source {
    content  = file("${path.module}/lambda/${each.key}/handler.py")
    filename = "handler.py"
  }
  source {
    content  = file("${path.module}/lambda/rack_configurations.py")
    filename = "rack_configurations.py"
  }
  source {
    content  = file("${path.module}/../../../../lib/python/lambda_http/__init__.py")
    filename = "lambda_http.py"
  }
  source {
    content  = file("${path.module}/../../../../lib/python/cache/__init__.py")
    filename = "cache.py"
  }
  output_path = "${path.module}/.terraform/lambda_packages/${each.key}.zip"
}

resource "aws_lambda_function" "verb" {
  for_each = local.verbs

  filename         = data.archive_file.verb[each.key].output_path
  function_name    = each.value.name
  role             = aws_iam_role.verb[each.key].arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.verb[each.key].output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 10
  memory_size      = 128
  description      = each.value.description

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT     = "true"
      DISTRIBUTION_ID           = data.terraform_remote_state.routing.outputs.distribution_id
      RACK_CONFIGURATIONS_TABLE = aws_dynamodb_table.configurations.name
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.verb[each.key].name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.verb[each.key].id]
  }
}

resource "aws_cloudwatch_log_group" "verb" {
  for_each = local.verbs

  name              = "/aws/lambda/${each.value.name}"
  retention_in_days = 7
}

resource "aws_lambda_permission" "verb" {
  for_each = local.verbs

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verb[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:${module.common.aws_region}:${module.common.aws_account_id}:${data.terraform_remote_state.routing.outputs.api_gateway_id}/*"
}

resource "aws_iam_role" "verb" {
  for_each = local.verbs

  name = "${each.value.name}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "verb_logs" {
  for_each = local.verbs

  name = "Logs"
  role = aws_iam_role.verb[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = ["${aws_cloudwatch_log_group.verb[each.key].arn}:*"]
    }]
  })
}

resource "aws_iam_role_policy" "verb_configurations" {
  for_each = local.verbs

  name = "Configurations"
  role = aws_iam_role.verb[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.actions
      Resource = [aws_dynamodb_table.configurations.arn]
    }]
  })
}

resource "aws_iam_role_policy" "store_invalidations" {
  name = "Invalidations"
  role = aws_iam_role.verb["store_rack_configuration"].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["cloudfront:CreateInvalidation"]
      Resource = ["arn:aws:cloudfront::${module.common.aws_account_id}:distribution/${data.terraform_remote_state.routing.outputs.distribution_id}"]
    }]
  })
}

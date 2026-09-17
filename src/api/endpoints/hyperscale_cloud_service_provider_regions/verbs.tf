locals {
  verbs = {
    list_regions = {
      name        = module.common.lambda_handler_names.list_regions
      description = "Lists the hyperscale cloud service provider regions in the store."
      actions     = ["dynamodb:Query"]
    }
    create_region = {
      name        = module.common.lambda_handler_names.create_region
      description = "Creates a hyperscale cloud service provider region under the next id the collection's counter holds."
      actions     = ["dynamodb:UpdateItem", "dynamodb:PutItem"]
    }
    read_region = {
      name        = module.common.lambda_handler_names.read_region
      description = "Serves a hyperscale cloud service provider region by its id."
      actions     = ["dynamodb:GetItem"]
    }
    correct_region = {
      name        = module.common.lambda_handler_names.correct_region
      description = "Corrects a hyperscale cloud service provider region by its id."
      actions     = ["dynamodb:PutItem"]
    }
    delete_region = {
      name        = module.common.lambda_handler_names.delete_region
      description = "Deletes a hyperscale cloud service provider region by its id."
      actions     = ["dynamodb:DeleteItem"]
    }
  }
  writes = toset(["create_region", "correct_region", "delete_region"])
}

data "archive_file" "verb" {
  for_each = local.verbs

  type = "zip"
  source {
    content  = file("${path.module}/lambda/${each.key}/handler.py")
    filename = "handler.py"
  }
  source {
    content  = file("${path.module}/lambda/regions.py")
    filename = "regions.py"
  }
  source {
    content  = file("${path.module}/../../../../lib/python/lambda_http/__init__.py")
    filename = "lambda_http.py"
  }
  source {
    content  = file("${path.module}/../../../../lib/python/store/__init__.py")
    filename = "store.py"
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
      AWS_USE_FIPS_ENDPOINT = "true"
      DISTRIBUTION_ID       = data.terraform_remote_state.routing.outputs.distribution_id
      STORE_TABLE           = data.terraform_remote_state.storage.outputs.table_name
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

resource "aws_iam_role_policy" "verb_store" {
  for_each = local.verbs

  name = "Store"
  role = aws_iam_role.verb[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = each.value.actions
      Resource = [data.terraform_remote_state.storage.outputs.table_arn]
    }]
  })
}

resource "aws_iam_role_policy" "verb_invalidations" {
  for_each = local.writes

  name = "Invalidations"
  role = aws_iam_role.verb[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["cloudfront:CreateInvalidation"]
      Resource = ["arn:aws:cloudfront::${module.common.aws_account_id}:distribution/${data.terraform_remote_state.routing.outputs.distribution_id}"]
    }]
  })
}

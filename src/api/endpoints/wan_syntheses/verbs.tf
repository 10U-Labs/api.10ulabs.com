locals {
  verbs = {
    list_wan_syntheses = {
      name        = module.common.lambda_handler_names.list_wan_syntheses
      description = "Lists the wan syntheses by id and label."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    read_wan_synthesis = {
      name        = module.common.lambda_handler_names.read_wan_synthesis
      description = "Serves a wan synthesis's record by its id."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_wan_pops = {
      name        = module.common.lambda_handler_names.list_wan_pops
      description = "Lists the wan pops of a synthesis's wan."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    read_wan_pop = {
      name        = module.common.lambda_handler_names.read_wan_pop
      description = "Serves a wan pop of a synthesis's wan by its id."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_backbone_circuits = {
      name        = module.common.lambda_handler_names.list_backbone_circuits
      description = "Lists the backbone circuits of a synthesis's wan."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_homing_circuits = {
      name        = module.common.lambda_handler_names.list_homing_circuits
      description = "Lists the homing circuits of a synthesis's wan."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_ridden_fiber = {
      name        = module.common.lambda_handler_names.list_ridden_fiber
      description = "Lists the fiber segments a synthesis's wan rides."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_sites = {
      name        = module.common.lambda_handler_names.list_sites
      description = "Lists the sites a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    read_site = {
      name        = module.common.lambda_handler_names.read_site
      description = "Serves a site a synthesis was given by its id."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_run_regions = {
      name        = module.common.lambda_handler_names.list_run_regions
      description = "Lists the hyperscale cloud service provider regions a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    read_run_region = {
      name        = module.common.lambda_handler_names.read_run_region
      description = "Serves a hyperscale cloud service provider region a synthesis was given by its id."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_off_net = {
      name        = module.common.lambda_handler_names.list_off_net
      description = "Lists the off-net pops a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_forced_wan_pops = {
      name        = module.common.lambda_handler_names.list_forced_wan_pops
      description = "Lists the forced wan pops a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_forced_circuits = {
      name        = module.common.lambda_handler_names.list_forced_circuits
      description = "Lists the forced circuits a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_forced_homes = {
      name        = module.common.lambda_handler_names.list_forced_homes
      description = "Lists the forced homes a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_prohibited_wan_pops = {
      name        = module.common.lambda_handler_names.list_prohibited_wan_pops
      description = "Lists the prohibited wan pops a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_prohibited_circuits = {
      name        = module.common.lambda_handler_names.list_prohibited_circuits
      description = "Lists the prohibited circuits a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    list_degree_exempt_wan_pops = {
      name        = module.common.lambda_handler_names.list_degree_exempt_wan_pops
      description = "Lists the degree-exempt wan pops a synthesis was given."
      actions     = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    create_wan_synthesis = {
      name        = module.common.lambda_handler_names.create_wan_synthesis
      description = "Creates a wan synthesis from a run's inputs, writing its record and list items under the next id and starting the synthesizer on it."
      actions     = ["dynamodb:UpdateItem", "dynamodb:PutItem"]
    }
    delete_wan_synthesis = {
      name        = module.common.lambda_handler_names.delete_wan_synthesis
      description = "Deletes a finished wan synthesis with everything under it."
      actions     = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchWriteItem", "dynamodb:DeleteItem"]
    }
  }
  sized = {
    create_wan_synthesis = { timeout = 30, memory_size = 256 }
    delete_wan_synthesis = { timeout = 30, memory_size = 256 }
  }
  writes = toset(["create_wan_synthesis", "delete_wan_synthesis"])
}

data "archive_file" "verb" {
  for_each = local.verbs

  type = "zip"
  source {
    content  = file("${path.module}/lambda/${each.key}/handler.py")
    filename = "handler.py"
  }
  source {
    content  = file("${path.module}/lambda/syntheses.py")
    filename = "syntheses.py"
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
  timeout          = try(local.sized[each.key].timeout, 10)
  memory_size      = try(local.sized[each.key].memory_size, 128)
  description      = each.value.description

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT = "true"
      DISTRIBUTION_ID       = data.terraform_remote_state.routing.outputs.distribution_id
      STORE_TABLE           = data.terraform_remote_state.storage.outputs.table_name
      SYNTHESIZER           = aws_lambda_function.synthesizer.function_name
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

resource "aws_iam_role_policy" "create_synthesizer" {
  name = "Synthesizer"
  role = aws_iam_role.verb["create_wan_synthesis"].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = [aws_lambda_function.synthesizer.arn]
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

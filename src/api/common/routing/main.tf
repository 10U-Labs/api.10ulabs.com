module "common" {
  source = "../../../../lib/opentofu/common"
}

locals {
  aws_region     = module.common.aws_region
  aws_account_id = module.common.aws_account_id
  names          = module.common.lambda_handler_names

  apigw_prefix = "arn:aws:apigateway:${local.aws_region}:lambda:path/2015-03-31/functions"
  lambda_arn   = "arn:aws:lambda:${local.aws_region}:${local.aws_account_id}:function"

  integration = {
    for key, name in local.names :
    key => "${local.apigw_prefix}/${local.lambda_arn}:${name}/invocations"
  }

  openapi_spec = templatefile("${path.module}/../../../www/api/openapi.json", {
    CatchAllHandlerArn    = local.integration.catchall
    DiagnosticsHandlerArn = local.integration.diagnostics
    HealthHandlerArn      = local.integration.health
  })
  spec_hash = substr(md5(local.openapi_spec), 0, 8)
}

resource "aws_api_gateway_rest_api" "api" {
  name = module.common.api_name
  body = local.openapi_spec

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_deployment" "prod" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeploy = local.spec_hash
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.prod.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "prod"
}

resource "aws_api_gateway_method_settings" "throttle" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  method_path = "*/*"

  settings {
    throttling_rate_limit  = 20
    throttling_burst_limit = 40
  }
}

locals {
  synthesizer_name     = "${local.function_name}-synthesizer"
  failure_handler_name = "${local.function_name}-failure-handler"
}

data "archive_file" "synthesizer" {
  type = "zip"
  dynamic "source" {
    for_each = fileset(path.module, "synthesizer/*.py")
    content {
      content  = file("${path.module}/${source.value}")
      filename = source.value
    }
  }
  source {
    content  = file("${path.module}/../../../../lib/python/lambda_http/__init__.py")
    filename = "lambda_http.py"
  }
  source {
    content  = file("${path.module}/../../../../lib/python/store/__init__.py")
    filename = "store.py"
  }
  output_path = "${path.module}/.terraform/lambda_packages/synthesizer.zip"
}

data "archive_file" "solver_layer" {
  type        = "zip"
  source_dir  = "${path.module}/.terraform/solver_layer"
  output_path = "${path.module}/.terraform/lambda_packages/solver_layer.zip"
}

resource "aws_lambda_layer_version" "solver" {
  filename                 = data.archive_file.solver_layer.output_path
  source_code_hash         = data.archive_file.solver_layer.output_base64sha256
  layer_name               = "${local.function_name}-solver"
  compatible_runtimes      = ["python3.13"]
  compatible_architectures = ["arm64"]
  description              = "highspy 1.15.1 and numpy 2.3.5: the solver the synthesizer's backbone search calls."
}

resource "aws_lambda_function" "synthesizer" {
  filename         = data.archive_file.synthesizer.output_path
  function_name    = local.synthesizer_name
  role             = aws_iam_role.synthesizer.arn
  handler          = "synthesizer.handler.lambda_handler"
  source_code_hash = data.archive_file.synthesizer.output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  layers           = [aws_lambda_layer_version.solver.arn]
  timeout          = 900
  memory_size      = 8192
  description      = "WAN synthesizer: reads a run's inputs and the carriers, computes its WAN and publishes it under the run with its status and figures."

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT = "true"
      STORE_TABLE           = data.terraform_remote_state.storage.outputs.table_name
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.synthesizer.name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.synthesizer.id]
  }
}

resource "aws_cloudwatch_log_group" "synthesizer" {
  name              = "/aws/lambda/${local.synthesizer_name}"
  retention_in_days = 7
}

resource "aws_lambda_function" "failure_handler" {
  filename         = data.archive_file.synthesizer.output_path
  function_name    = local.failure_handler_name
  role             = aws_iam_role.failure_handler.arn
  handler          = "synthesizer.failure_handler.lambda_handler"
  source_code_hash = data.archive_file.synthesizer.output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 128
  description      = "WAN failure handler: marks a run timeout when AWS kills its synthesizer."

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT = "true"
      STORE_TABLE           = data.terraform_remote_state.storage.outputs.table_name
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.failure_handler.name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.failure_handler.id]
  }
}

resource "aws_cloudwatch_log_group" "failure_handler" {
  name              = "/aws/lambda/${local.failure_handler_name}"
  retention_in_days = 7
}

resource "aws_lambda_function_event_invoke_config" "synthesizer" {
  function_name          = aws_lambda_function.synthesizer.function_name
  maximum_retry_attempts = 0

  destination_config {
    on_failure {
      destination = aws_lambda_function.failure_handler.arn
    }
  }
}

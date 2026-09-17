resource "aws_iam_role" "synthesizer" {
  name = "${local.synthesizer_name}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "synthesizer_logs" {
  name = "Logs"
  role = aws_iam_role.synthesizer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = ["${aws_cloudwatch_log_group.synthesizer.arn}:*"]
    }]
  })
}

resource "aws_iam_role_policy" "synthesizer_store" {
  name = "Store"
  role = aws_iam_role.synthesizer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"]
      Resource = [data.terraform_remote_state.storage.outputs.table_arn]
    }]
  })
}

resource "aws_iam_role_policy" "synthesizer_failure_handler" {
  name = "FailureHandler"
  role = aws_iam_role.synthesizer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = [aws_lambda_function.failure_handler.arn]
    }]
  })
}

resource "aws_iam_role_policy" "synthesizer_invalidations" {
  name = "Invalidations"
  role = aws_iam_role.synthesizer.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["cloudfront:CreateInvalidation"]
      Resource = ["arn:aws:cloudfront::${module.common.aws_account_id}:distribution/${data.terraform_remote_state.routing.outputs.distribution_id}"]
    }]
  })
}

resource "aws_iam_role" "failure_handler" {
  name = "${local.failure_handler_name}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "failure_handler_logs" {
  name = "Logs"
  role = aws_iam_role.failure_handler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = ["${aws_cloudwatch_log_group.failure_handler.arn}:*"]
    }]
  })
}

resource "aws_iam_role_policy" "failure_handler_store" {
  name = "Store"
  role = aws_iam_role.failure_handler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem"]
      Resource = [data.terraform_remote_state.storage.outputs.table_arn]
    }]
  })
}

resource "aws_iam_role_policy" "failure_handler_invalidations" {
  name = "Invalidations"
  role = aws_iam_role.failure_handler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["cloudfront:CreateInvalidation"]
      Resource = ["arn:aws:cloudfront::${module.common.aws_account_id}:distribution/${data.terraform_remote_state.routing.outputs.distribution_id}"]
    }]
  })
}

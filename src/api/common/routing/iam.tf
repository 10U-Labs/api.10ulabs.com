resource "aws_iam_role" "catchall" {
  name = "${local.names.catchall}-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "catchall_logs" {
  name = "Logs"
  role = aws_iam_role.catchall.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = ["${aws_cloudwatch_log_group.catchall.arn}:*"]
    }]
  })
}

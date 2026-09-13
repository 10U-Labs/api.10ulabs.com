resource "aws_s3_bucket" "analytics" {
  bucket = local.bucket_name
}

resource "aws_s3_bucket_versioning" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  rule {
    id     = "expire-old-exports"
    status = "Enabled"

    expiration {
      days = 90
    }

    filter {
      prefix = "exports/"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "archive_file" "export" {
  type        = "zip"
  source_file = "${path.module}/lambda/exporter/handler.py"
  output_path = "${path.module}/.terraform/lambda_packages/export.zip"
}

resource "aws_lambda_function" "export" {
  filename         = data.archive_file.export.output_path
  function_name    = local.export_name
  role             = aws_iam_role.export.arn
  handler          = "handler.lambda_handler"
  source_code_hash = data.archive_file.export.output_base64sha256
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  memory_size      = 128
  description      = "Sessions export: start a point-in-time export of the events table to the analytics bucket."

  environment {
    variables = {
      AWS_USE_FIPS_ENDPOINT = "true"
      DYNAMODB_TABLE_ARN    = aws_dynamodb_table.events.arn
      S3_BUCKET             = aws_s3_bucket.analytics.bucket
      S3_PREFIX             = "exports/events"
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.export.name
  }

  lifecycle {
    replace_triggered_by = [aws_iam_role.export.id]
  }
}

resource "aws_cloudwatch_log_group" "export" {
  name              = "/aws/lambda/${local.export_name}"
  retention_in_days = 7
}

resource "aws_scheduler_schedule" "daily_export" {
  name       = local.export_name
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = "cron(0 5 * * ? *)"
  schedule_expression_timezone = "UTC"

  target {
    arn      = aws_lambda_function.export.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}

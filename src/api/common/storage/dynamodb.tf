resource "aws_dynamodb_table" "store" {
  name           = local.table_name
  billing_mode   = "PROVISIONED"
  read_capacity  = 15
  write_capacity = 15
  hash_key       = "PK"
  range_key      = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }
}

data "aws_iam_policy_document" "store" {
  statement {
    sid       = "DenyEveryPrincipalOutsideTheAccount"
    effect    = "Deny"
    actions   = ["dynamodb:*"]
    resources = [aws_dynamodb_table.store.arn]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "StringNotEquals"
      variable = "aws:PrincipalAccount"
      values   = [module.common.aws_account_id]
    }
  }
}

resource "aws_dynamodb_resource_policy" "store" {
  resource_arn = aws_dynamodb_table.store.arn
  policy       = data.aws_iam_policy_document.store.json
}

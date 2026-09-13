resource "aws_backup_vault" "configurations" {
  name = local.backup_name
}

resource "aws_backup_plan" "configurations" {
  name = local.backup_name

  rule {
    rule_name         = "daily-backup"
    target_vault_name = aws_backup_vault.configurations.name
    schedule          = "cron(0 5 * * ? *)"

    lifecycle {
      delete_after = 30
    }
  }
}

resource "aws_iam_role" "backup" {
  name = local.backup_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "backup.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "restores" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

resource "aws_backup_selection" "configurations" {
  name         = local.backup_name
  plan_id      = aws_backup_plan.configurations.id
  iam_role_arn = aws_iam_role.backup.arn

  resources = [aws_dynamodb_table.configurations.arn]
}

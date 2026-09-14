locals {
  product      = module.common.product
  account      = module.common.aws_account_id
  region       = module.common.aws_region
  state_bucket = "arn:aws:s3:::${module.common.state_bucket}"
  functions    = "arn:aws:lambda:${local.region}:${local.account}:function:${local.product}-*"
  log_groups   = "arn:aws:logs:${local.region}:${local.account}:log-group:/aws/lambda/${local.product}-*"
  log_listing  = "arn:aws:logs:${local.region}:${local.account}:log-group::log-stream:"
  lambda_roles = "arn:aws:iam::${local.account}:role/${local.product}-*"
  gateway_role = "arn:aws:iam::${local.account}:role/aws-service-role/ops.apigateway.amazonaws.com/AWSServiceRoleForAPIGateway"
  rest_apis    = "arn:aws:apigateway:${local.region}::/restapis"
  parameters   = "arn:aws:ssm:${local.region}:${local.account}:parameter/${local.product}/*"
  api_params   = "arn:aws:ssm:${local.region}:${local.account}:parameter/${module.common.api_name}/*"
  identities   = "arn:aws:ses:${local.region}:${local.account}:identity/*@${module.common.domain_name}"
  tables       = "arn:aws:dynamodb:${local.region}:${local.account}:table/${local.product}-*"
  vaults       = "arn:aws:backup:${local.region}:${local.account}:backup-vault:${local.product}-*"
  plans        = "arn:aws:backup:${local.region}:${local.account}:backup-plan:*"
  backup_roles = "arn:aws:iam::${local.account}:role/${local.product}-*-backup"
  buckets      = "arn:aws:s3:::${local.product}-*"
  schedules    = "arn:aws:scheduler:${local.region}:${local.account}:schedule/default/${local.product}-*"
  sched_roles  = "arn:aws:iam::${local.account}:role/${local.product}-*-scheduler"
  backup_key   = "arn:aws:kms:${local.region}:${local.account}:key/481c2fb8-f0da-494c-910e-4b09da6dc5c3"
  self         = "arn:aws:iam::${local.account}:role/${local.role_name}"
  backup_policies = [
    "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup",
    "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores",
  ]
}

data "aws_iam_policy_document" "state" {
  statement {
    sid       = "ListTheStateBucket"
    actions   = ["s3:ListBucket"]
    resources = [local.state_bucket]
  }

  statement {
    sid       = "ReadWriteAndLockThisRepositoryState"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${local.state_bucket}/api.10ulabs.com/*"]
  }
}

data "aws_iam_policy_document" "functions" {
  statement {
    sid = "DeclareTheHandlers"
    actions = [
      "lambda:CreateFunction",
      "lambda:DeleteFunction",
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:ListVersionsByFunction",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:GetPolicy",
      "lambda:AddPermission",
      "lambda:RemovePermission",
      "lambda:ListTags",
      "lambda:TagResource",
      "lambda:UntagResource",
    ]
    resources = [local.functions]
  }

  statement {
    sid       = "ListEveryFunctionToFindALeftover"
    actions   = ["lambda:ListFunctions"]
    resources = ["*"]
  }

  statement {
    sid       = "DescribeLogGroupsOnTheArnIamEvaluatesItAgainst"
    actions   = ["logs:DescribeLogGroups"]
    resources = [local.log_listing]
  }

  statement {
    sid = "KeepTheHandlersLogGroups"
    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:PutRetentionPolicy",
      "logs:ListTagsForResource",
      "logs:TagResource",
      "logs:UntagResource",
    ]
    resources = [local.log_groups]
  }
}

data "aws_iam_policy_document" "roles" {
  statement {
    sid = "DeclareTheHandlersRoles"
    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:ListRolePolicies",
      "iam:GetRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:DetachRolePolicy",
      "iam:ListInstanceProfilesForRole",
      "iam:TagRole",
      "iam:UntagRole",
    ]
    resources = [local.lambda_roles]
  }

  statement {
    sid       = "HandTheHandlersRolesToLambdaAlone"
    actions   = ["iam:PassRole"]
    resources = [local.lambda_roles]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }

  statement {
    sid       = "HandTheBackupRolesToBackupAlone"
    actions   = ["iam:PassRole"]
    resources = [local.backup_roles]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["backup.amazonaws.com"]
    }
  }

  statement {
    sid       = "HandTheSchedulerRolesToSchedulerAlone"
    actions   = ["iam:PassRole"]
    resources = [local.sched_roles]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["scheduler.amazonaws.com"]
    }
  }

  statement {
    sid       = "AttachOnlyTheBackupPoliciesAndOnlyToTheBackupRoles"
    actions   = ["iam:AttachRolePolicy"]
    resources = [local.backup_roles]

    condition {
      test     = "ForAnyValue:StringEquals"
      variable = "iam:PolicyARN"
      values   = local.backup_policies
    }
  }

  statement {
    sid       = "LetApiGatewayAskForItsServiceRole"
    actions   = ["iam:CreateServiceLinkedRole"]
    resources = [local.gateway_role]

    condition {
      test     = "StringEquals"
      variable = "iam:AWSServiceName"
      values   = ["ops.apigateway.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "routing" {
  statement {
    sid = "DeclareTheApi"
    actions = [
      "apigateway:GET",
      "apigateway:POST",
      "apigateway:PUT",
      "apigateway:PATCH",
      "apigateway:DELETE",
    ]
    resources = [
      local.rest_apis,
      "${local.rest_apis}/*",
      "arn:aws:apigateway:${local.region}::/tags/*",
    ]
  }

  statement {
    sid = "KeepTheProductsParameters"
    actions = [
      "ssm:PutParameter",
      "ssm:GetParameter",
      "ssm:DeleteParameter",
      "ssm:ListTagsForResource",
      "ssm:AddTagsToResource",
      "ssm:RemoveTagsFromResource",
    ]
    resources = [local.parameters, local.api_params]
  }

  statement {
    sid       = "DescribeParametersToReadATier"
    actions   = ["ssm:DescribeParameters"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "storage" {
  statement {
    sid = "DeclareTheTables"
    actions = [
      "dynamodb:CreateTable",
      "dynamodb:DeleteTable",
      "dynamodb:DescribeTable",
      "dynamodb:UpdateTable",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:UpdateContinuousBackups",
      "dynamodb:DescribeTimeToLive",
      "dynamodb:GetResourcePolicy",
      "dynamodb:PutResourcePolicy",
      "dynamodb:DeleteResourcePolicy",
      "dynamodb:ListTagsOfResource",
      "dynamodb:TagResource",
      "dynamodb:UntagResource",
    ]
    resources = [local.tables]
  }

  statement {
    sid = "DeclareTheBuckets"
    actions = [
      "s3:CreateBucket",
      "s3:ListBucket",
      "s3:ListBucketVersions",
      "s3:GetAccelerateConfiguration",
      "s3:GetBucketAcl",
      "s3:GetBucketCORS",
      "s3:GetBucketLogging",
      "s3:GetBucketObjectLockConfiguration",
      "s3:GetBucketPolicy",
      "s3:GetBucketPublicAccessBlock",
      "s3:PutBucketPublicAccessBlock",
      "s3:GetBucketRequestPayment",
      "s3:GetBucketTagging",
      "s3:PutBucketTagging",
      "s3:GetBucketVersioning",
      "s3:PutBucketVersioning",
      "s3:GetBucketWebsite",
      "s3:GetEncryptionConfiguration",
      "s3:GetLifecycleConfiguration",
      "s3:PutLifecycleConfiguration",
      "s3:GetReplicationConfiguration",
    ]
    resources = [local.buckets]
  }

  statement {
    sid = "DeclareTheBackupVaults"
    actions = [
      "backup:CreateBackupVault",
      "backup:DeleteBackupVault",
      "backup:DescribeBackupVault",
      "backup:ListTags",
      "backup:TagResource",
      "backup:UntagResource",
    ]
    resources = [local.vaults]
  }

  statement {
    sid = "DeclareTheBackupPlansAndSelections"
    actions = [
      "backup:CreateBackupPlan",
      "backup:DeleteBackupPlan",
      "backup:GetBackupPlan",
      "backup:UpdateBackupPlan",
      "backup:CreateBackupSelection",
      "backup:DeleteBackupSelection",
      "backup:GetBackupSelection",
      "backup:ListTags",
      "backup:TagResource",
      "backup:UntagResource",
    ]
    resources = [local.plans]
  }

  statement {
    sid       = "MountTheVaultCapsuleThatTakesNoResource"
    actions   = ["backup-storage:MountCapsule"]
    resources = ["*"]
  }

  statement {
    sid = "SealTheVaultsWithTheBackupKey"
    actions = [
      "kms:CreateGrant",
      "kms:Decrypt",
      "kms:DescribeKey",
      "kms:GenerateDataKey",
      "kms:RetireGrant",
    ]
    resources = [local.backup_key]
  }
}

data "aws_iam_policy_document" "schedules" {
  statement {
    sid = "DeclareTheSchedules"
    actions = [
      "scheduler:CreateSchedule",
      "scheduler:DeleteSchedule",
      "scheduler:GetSchedule",
      "scheduler:UpdateSchedule",
      "scheduler:ListTagsForResource",
      "scheduler:TagResource",
      "scheduler:UntagResource",
    ]
    resources = [local.schedules]
  }
}

data "aws_iam_policy_document" "ses" {
  statement {
    sid       = "DeclareTheSendingIdentities"
    actions   = ["ses:VerifyEmailIdentity", "ses:DeleteIdentity"]
    resources = [local.identities]
  }

  statement {
    sid       = "ReadIdentityVerificationOnTheArnSesEvaluatesItAgainst"
    actions   = ["ses:GetIdentityVerificationAttributes"]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "self" {
  statement {
    sid = "ReconcileThisRole"
    actions = [
      "iam:GetRole",
      "iam:UpdateRole",
      "iam:UpdateRoleDescription",
      "iam:UpdateAssumeRolePolicy",
      "iam:ListRolePolicies",
      "iam:GetRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:DetachRolePolicy",
      "iam:ListInstanceProfilesForRole",
      "iam:TagRole",
      "iam:UntagRole",
    ]
    resources = [local.self]
  }

  statement {
    sid       = "ReadTheGitHubProvider"
    actions   = ["iam:GetOpenIDConnectProvider"]
    resources = [data.aws_iam_openid_connect_provider.github.arn]
  }
}

resource "aws_iam_role_policy" "state" {
  name   = "State"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.state.json
}

resource "aws_iam_role_policy" "functions" {
  name   = "Functions"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.functions.json
}

resource "aws_iam_role_policy" "roles" {
  name   = "Roles"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.roles.json
}

resource "aws_iam_role_policy" "routing" {
  name   = "Routing"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.routing.json
}

resource "aws_iam_role_policy" "storage" {
  name   = "Storage"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.storage.json
}

resource "aws_iam_role_policy" "schedules" {
  name   = "Schedules"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.schedules.json
}

resource "aws_iam_role_policy" "ses" {
  name   = "Ses"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.ses.json
}

resource "aws_iam_role_policy" "self" {
  name   = "Self"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.self.json
}

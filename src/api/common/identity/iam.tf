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
  self         = "arn:aws:iam::${local.account}:role/${local.role_name}"
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
}

data "aws_iam_policy_document" "self" {
  statement {
    sid = "ReconcileThisRole"
    actions = [
      "iam:GetRole",
      "iam:UpdateRole",
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

resource "aws_iam_role_policy" "self" {
  name   = "Self"
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.self.json
}

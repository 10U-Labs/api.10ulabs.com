module "common" {
  source = "../../../../lib/opentofu/common"
}

locals {
  role_name  = module.common.deploy_role_name
  issuer     = "token.actions.githubusercontent.com"
  repository = "10U-Labs@240548037/api.10ulabs.com@1368777392"
  ref        = "refs/heads/main"
  subject    = "repo:${local.repository}:ref:${local.ref}"
}

data "aws_iam_openid_connect_provider" "github" {
  arn = "arn:aws:iam::${module.common.aws_account_id}:oidc-provider/${local.issuer}"
}

data "aws_iam_policy_document" "trust" {
  statement {
    sid     = "GitHubActionsOnMain"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.issuer}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.issuer}:sub"
      values   = [local.subject]
    }
  }
}

import {
  to = aws_iam_role.deploy
  id = "TenULabsApiRole"
}

import {
  to = aws_iam_role_policy.state
  id = "TenULabsApiRole:State"
}

import {
  to = aws_iam_role_policy.self
  id = "TenULabsApiRole:Self"
}

resource "aws_iam_role" "deploy" {
  name                 = local.role_name
  description          = "The role every workflow of 10U-Labs/api.10ulabs.com assumes: pushes to main alone, over the resources the stacks declare and nothing wider."
  assume_role_policy   = data.aws_iam_policy_document.trust.json
  max_session_duration = 3600
}

resource "aws_iam_role_policy_attachments_exclusive" "deploy" {
  role_name   = aws_iam_role.deploy.name
  policy_arns = []

  depends_on = [aws_iam_role_policies_exclusive.deploy]
}

resource "aws_iam_role_policies_exclusive" "deploy" {
  role_name = aws_iam_role.deploy.name
  policy_names = [
    aws_iam_role_policy.state.name,
    aws_iam_role_policy.functions.name,
    aws_iam_role_policy.roles.name,
    aws_iam_role_policy.routing.name,
    aws_iam_role_policy.ses.name,
    aws_iam_role_policy.self.name,
  ]
}

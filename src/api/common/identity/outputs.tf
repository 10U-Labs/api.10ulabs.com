output "role_arn" {
  description = "ARN of the role every workflow assumes, which vars.OIDC_ROLE_ARN must equal."
  value       = aws_iam_role.deploy.arn
}

output "subject" {
  description = "The one GitHub OIDC subject the trust admits: this repository by its immutable ids, on main."
  value       = local.subject
}

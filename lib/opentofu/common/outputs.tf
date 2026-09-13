output "aws_account_id" {
  description = "The AWS account every stack deploys into."
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "The region every stack deploys into."
  value       = "us-east-2"
}

output "state_bucket" {
  description = "The shared OpenTofu state bucket; every stack's key is api.10ulabs.com/<directory>/terraform.tfstate."
  value       = "10ulabs-terraform-state-us-east-2"
}

output "product" {
  description = "The prefix every resource this repository owns is named under."
  value       = "api-10ulabs-com"
}

output "domain_name" {
  description = "The domain the API and the addresses it sends from live under."
  value       = "10ulabs.com"
}

output "api_name" {
  description = "The REST API's name, and the host it is served as."
  value       = "api.10ulabs.com"
}

output "deploy_role_name" {
  description = "The role every workflow assumes, declared by src/api/common/identity."
  value       = "TenULabsApiRole"
}

output "lambda_handler_names" {
  description = "Deterministic Lambda function names, one per handler, which the routing stack composes into integration URIs."
  value = {
    catchall            = "api-10ulabs-com-catchall"
    contact             = "api-10ulabs-com-contact"
    diagnostics         = "api-10ulabs-com-diagnostics"
    health              = "api-10ulabs-com-health"
    rack_configurations = "api-10ulabs-com-rack-configurations"
  }
}

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
  description = "The host with its dots replaced: the name of the bucket behind it and the prefix every other resource this repository owns is named under."
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
  description = "Deterministic Lambda function names, one per Lambda, whether a stack's single handler or a row of its verbs table, and the authorizer in front of the protected routes, which the routing stack composes into integration URIs; a route reaches its Lambda only once the stack declaring it has applied, after routing, so a Lambda's deployed tests live in its own stack."
  value = {
    add_fiber_segment     = "api-10ulabs-com-add-fiber-segment"
    add_pop               = "api-10ulabs-com-add-pop"
    authorizer            = "api-10ulabs-com-authorizer"
    catchall              = "api-10ulabs-com-catchall"
    contact               = "api-10ulabs-com-contact"
    correct_fiber_segment = "api-10ulabs-com-correct-fiber-segment"
    correct_pop           = "api-10ulabs-com-correct-pop"
    correct_region        = "api-10ulabs-com-correct-region"
    create_carrier        = "api-10ulabs-com-create-carrier"
    create_region         = "api-10ulabs-com-create-region"
    delete_carrier        = "api-10ulabs-com-delete-carrier"
    delete_region         = "api-10ulabs-com-delete-region"
    diagnostics           = "api-10ulabs-com-diagnostics"
    health                = "api-10ulabs-com-health"
    list_carriers         = "api-10ulabs-com-list-carriers"
    list_fiber_segments   = "api-10ulabs-com-list-fiber-segments"
    list_pops             = "api-10ulabs-com-list-pops"
    list_regions          = "api-10ulabs-com-list-regions"
    rack_configurations   = "api-10ulabs-com-rack-configurations"
    read_carrier          = "api-10ulabs-com-read-carrier"
    read_fiber_segment    = "api-10ulabs-com-read-fiber-segment"
    read_pop              = "api-10ulabs-com-read-pop"
    read_region           = "api-10ulabs-com-read-region"
    remove_fiber_segment  = "api-10ulabs-com-remove-fiber-segment"
    remove_pop            = "api-10ulabs-com-remove-pop"
    rename_carrier        = "api-10ulabs-com-rename-carrier"
    sessions              = "api-10ulabs-com-sessions"
    wan_syntheses         = "api-10ulabs-com-wan-syntheses"
    wan_syntheses_writer  = "api-10ulabs-com-wan-syntheses-writer"
  }
}

output "hosted_zone_id" {
  description = "The Route 53 zone of the domain, where the API's name and its certificate's validation record live."
  value       = "Z07722121TJUMGGCZYKBV"
}

output "logs_bucket" {
  description = "The account's central logs bucket, declared by 10ulabs.com's bootstrap, where the distribution and the host's bucket write their access logs."
  value       = "10ulabs-central-logs-us-east-2"
}

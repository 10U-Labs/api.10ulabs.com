terraform {
  backend "s3" {
    bucket       = "10ulabs-terraform-state-us-east-2"
    key          = "api.10ulabs.com/src/api/operational/health/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }

  required_version = ">= 1.11"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"

  default_tags {
    tags = {
      ManagedBy  = "OpenTofu"
      Project    = "api.10ulabs.com"
      Repository = "10U-Labs/api.10ulabs.com"
      Stack      = "operational/diagnostics"
    }
  }
}

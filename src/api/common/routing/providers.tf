provider "aws" {
  region = "us-east-2"

  default_tags {
    tags = {
      ManagedBy  = "OpenTofu"
      Project    = "api.10ulabs.com"
      Repository = "10U-Labs/api.10ulabs.com"
      Stack      = "common/routing"
    }
  }
}

provider "aws" {
  alias  = "us-east-1"
  region = "us-east-1"

  default_tags {
    tags = {
      ManagedBy  = "OpenTofu"
      Project    = "api.10ulabs.com"
      Repository = "10U-Labs/api.10ulabs.com"
      Stack      = "common/routing"
    }
  }
}

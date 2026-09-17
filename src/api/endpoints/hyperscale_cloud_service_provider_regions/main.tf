module "common" {
  source = "../../../../lib/opentofu/common"
}

data "terraform_remote_state" "routing" {
  backend = "s3"

  config = {
    bucket = module.common.state_bucket
    key    = "api.10ulabs.com/src/api/common/routing/terraform.tfstate"
    region = module.common.aws_region
  }
}

data "terraform_remote_state" "storage" {
  backend = "s3"

  config = {
    bucket = module.common.state_bucket
    key    = "api.10ulabs.com/src/api/common/storage/terraform.tfstate"
    region = module.common.aws_region
  }
}

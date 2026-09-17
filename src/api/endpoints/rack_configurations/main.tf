module "common" {
  source = "../../../../lib/opentofu/common"
}

locals {
  table_name  = "${module.common.product}-rack-configurations"
  backup_name = "${module.common.product}-rack-configurations-backup"
}

data "terraform_remote_state" "routing" {
  backend = "s3"

  config = {
    bucket = module.common.state_bucket
    key    = "api.10ulabs.com/src/api/common/routing/terraform.tfstate"
    region = module.common.aws_region
  }
}

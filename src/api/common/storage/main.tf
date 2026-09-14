module "common" {
  source = "../../../../lib/opentofu/common"
}

locals {
  table_name = "${module.common.product}-store"
}

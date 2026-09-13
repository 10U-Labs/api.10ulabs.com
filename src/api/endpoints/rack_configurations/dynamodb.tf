resource "aws_dynamodb_table" "configurations" {
  name           = local.table_name
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "config_hash"

  attribute {
    name = "config_hash"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

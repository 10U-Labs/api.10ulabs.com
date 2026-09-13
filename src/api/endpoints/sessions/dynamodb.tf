resource "aws_dynamodb_table" "events" {
  name           = local.table_name
  billing_mode   = "PROVISIONED"
  read_capacity  = 2
  write_capacity = 2
  hash_key       = "session_id"
  range_key      = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "event_type"
    type = "S"
  }

  attribute {
    name = "device_id"
    type = "S"
  }

  global_secondary_index {
    name            = "event_type-index"
    hash_key        = "event_type"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = 2
    write_capacity  = 2
  }

  global_secondary_index {
    name            = "device_id-index"
    hash_key        = "device_id"
    range_key       = "timestamp"
    projection_type = "ALL"
    read_capacity   = 2
    write_capacity  = 2
  }

  point_in_time_recovery {
    enabled = true
  }
}

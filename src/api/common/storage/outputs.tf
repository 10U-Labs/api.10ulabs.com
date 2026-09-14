output "table_name" {
  description = "The one table this repository's API reads and writes; each handler stack names it in its environment."
  value       = aws_dynamodb_table.store.name
}

output "table_arn" {
  description = "The table's ARN; each handler stack grants its role the verbs it uses on it."
  value       = aws_dynamodb_table.store.arn
}

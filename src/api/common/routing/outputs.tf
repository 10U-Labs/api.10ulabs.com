output "api_gateway_id" {
  description = "REST API id; each handler stack scopes its invoke permission to it."
  value       = aws_api_gateway_rest_api.api.id
}

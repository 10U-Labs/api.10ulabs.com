output "api_gateway_id" {
  description = "REST API id; each handler stack scopes its invoke permission to it."
  value       = aws_api_gateway_rest_api.api.id
}

output "distribution_id" {
  description = "The distribution in front of the API; a write Lambda names it to invalidate the cache entries its change stales."
  value       = aws_cloudfront_distribution.api.id
}

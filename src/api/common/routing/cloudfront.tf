locals {
  www_bucket   = module.common.product
  logs_bucket  = module.common.logs_bucket
  logs_domain  = "${local.logs_bucket}.s3.amazonaws.com"
  gateway_host = "${aws_api_gateway_rest_api.api.id}.execute-api.${local.aws_region}.amazonaws.com"
}

resource "aws_s3_bucket" "www" {
  bucket        = local.www_bucket
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "www" {
  bucket = aws_s3_bucket.www.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "www" {
  bucket = aws_s3_bucket.www.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_logging" "www" {
  bucket = aws_s3_bucket.www.id

  target_bucket = local.logs_bucket
  target_prefix = "s3-access/${module.common.api_name}/"
}

resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.www.id
  key          = "index.html"
  source       = "${path.module}/../../../www/index.html"
  content_type = "text/html"
  etag         = filemd5("${path.module}/../../../www/index.html")
}

resource "aws_s3_object" "spec" {
  bucket        = aws_s3_bucket.www.id
  key           = "openapi.json"
  source        = "${path.module}/../../../www/openapi.json"
  content_type  = "application/json"
  cache_control = "max-age=60"
  etag          = filemd5("${path.module}/../../../www/openapi.json")
}

resource "aws_s3_object" "not_found" {
  bucket       = aws_s3_bucket.www.id
  key          = "404.html"
  source       = "${path.module}/../../../www/404.html"
  content_type = "text/html"
  etag         = filemd5("${path.module}/../../../www/404.html")
}

resource "aws_cloudfront_origin_access_control" "www" {
  name                              = local.www_bucket
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_s3_bucket_policy" "www" {
  bucket = aws_s3_bucket.www.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "ReadForTheDistributionAlone"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.www.arn}/*"
      Condition = {
        StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.api.arn }
      }
    }]
  })
}

resource "aws_cloudfront_cache_policy" "www" {
  name        = local.www_bucket
  min_ttl     = 60
  default_ttl = 86400
  max_ttl     = 31536000

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }

    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

resource "aws_cloudfront_function" "root" {
  name    = "${module.common.product}-root"
  runtime = "cloudfront-js-2.0"
  publish = true
  code    = <<-EOT
    function handler(event) {
        var request = event.request;
        if (request.uri === '/') {
            request.uri = '/index.html';
        }
        return request;
    }
  EOT
}

data "aws_cloudfront_cache_policy" "disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host_header" {
  name = "Managed-AllViewerExceptHostHeader"
}

data "aws_cloudfront_origin_request_policy" "cors_s3_origin" {
  name = "Managed-CORS-S3Origin"
}

resource "aws_cloudfront_distribution" "api" {
  enabled = true
  comment = module.common.api_name
  aliases = [module.common.api_name]

  logging_config {
    include_cookies = false
    bucket          = local.logs_domain
    prefix          = "cloudfront-logs/${module.common.api_name}/"
  }

  origin {
    domain_name = local.gateway_host
    origin_id   = "gateway"
    origin_path = "/${aws_api_gateway_stage.prod.stage_name}"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  origin {
    domain_name              = aws_s3_bucket.www.bucket_regional_domain_name
    origin_id                = "www"
    origin_access_control_id = aws_cloudfront_origin_access_control.www.id
  }

  default_cache_behavior {
    target_origin_id       = "gateway"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host_header.id
  }

  ordered_cache_behavior {
    path_pattern           = "/"
    target_origin_id       = "www"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id          = aws_cloudfront_cache_policy.www.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.cors_s3_origin.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.root.arn
    }
  }

  ordered_cache_behavior {
    path_pattern           = "/openapi.json"
    target_origin_id       = "www"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id          = aws_cloudfront_cache_policy.www.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.cors_s3_origin.id
  }

  ordered_cache_behavior {
    path_pattern           = "/404.html"
    target_origin_id       = "www"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id          = aws_cloudfront_cache_policy.www.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.cors_s3_origin.id
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.api.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
}

resource "aws_route53_record" "api" {
  zone_id         = module.common.hosted_zone_id
  name            = module.common.api_name
  type            = "A"
  allow_overwrite = true

  alias {
    name                   = aws_cloudfront_distribution.api.domain_name
    zone_id                = aws_cloudfront_distribution.api.hosted_zone_id
    evaluate_target_health = false
  }
}

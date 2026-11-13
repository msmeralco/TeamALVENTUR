output "bucket" {
  description = "S3 bucket to upload web/dist to."
  value       = aws_s3_bucket.web.bucket
}

output "distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation after a deploy)."
  value       = aws_cloudfront_distribution.web.id
}

output "domain" {
  description = "CloudFront domain for the web app, API, and mobile PoC API."
  value       = aws_cloudfront_distribution.web.domain_name
}

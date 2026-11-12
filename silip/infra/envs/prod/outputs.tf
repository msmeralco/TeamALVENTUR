output "web_domain" {
  description = "CloudFront domain. Copy into web_domain and apply again for Cognito callbacks."
  value       = module.web.domain
}

output "web_url" {
  description = "Public URL of the web app (and /api)."
  value       = "https://${module.web.domain}"
}

output "web_bucket" {
  description = "Upload web/dist here."
  value       = module.web.bucket
}

output "distribution_id" {
  description = "Invalidate this after uploading web/dist."
  value       = module.web.distribution_id
}

output "ecr_repository_url" {
  description = "Push the API image here before applying a new image_tag."
  value       = module.api.repository_url
}

output "cognito_user_pool_id" {
  description = "COGNITO_USER_POOL_ID, and for inviting users."
  value       = module.auth.user_pool_id
}

output "cognito_client_id" {
  description = "VITE_COGNITO_CLIENT_ID."
  value       = module.auth.client_id
}

output "cognito_authority" {
  description = "VITE_COGNITO_AUTHORITY."
  value       = module.auth.authority
}

output "cognito_domain_url" {
  description = "VITE_COGNITO_DOMAIN."
  value       = module.auth.domain_url
}

output "database_secret_arn" {
  description = "Put the Neon pooled URL here once: aws secretsmanager put-secret-value."
  value       = module.api.database_secret_arn
}

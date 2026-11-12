output "user_pool_id" {
  description = "Cognito user pool ID (COGNITO_USER_POOL_ID)."
  value       = aws_cognito_user_pool.this.id
}

output "client_id" {
  description = "Public app client ID (COGNITO_CLIENT_ID, VITE_COGNITO_CLIENT_ID)."
  value       = aws_cognito_user_pool_client.web.id
}

output "authority" {
  description = "OIDC authority for the web app (VITE_COGNITO_AUTHORITY)."
  value       = "https://${aws_cognito_user_pool.this.endpoint}"
}

output "domain_url" {
  description = "Managed login base URL (VITE_COGNITO_DOMAIN)."
  value       = "https://${aws_cognito_user_pool_domain.this.domain}.auth.${data.aws_region.current.region}.amazoncognito.com"
}

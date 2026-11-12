output "repository_url" {
  description = "ECR repository to push the API image to."
  value       = aws_ecr_repository.api.repository_url
}

output "api_function_name" {
  description = "API Lambda name (CloudFront origin access is granted on it)."
  value       = aws_lambda_function.function["api"].function_name
}

output "api_function_url" {
  description = "API Lambda function URL (reachable only through CloudFront)."
  value       = aws_lambda_function_url.api.function_url
}

output "database_secret_arn" {
  description = "Secrets Manager secret the Lambdas read DATABASE_URL from."
  value       = aws_secretsmanager_secret.database_url.arn
}

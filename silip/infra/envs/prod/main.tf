locals {
  environment = "prod"
  name        = "${var.project}-${local.environment}"
  # Cognito callbacks: local dev always, CloudFront once its domain is known (see web_domain).
  web_origins = concat(["http://localhost:5173"], var.web_domain == null ? [] : ["https://${var.web_domain}"])
}

module "auth" {
  source              = "../../modules/auth"
  name                = local.name
  domain_prefix       = "${var.cognito_domain_prefix}-${local.environment}"
  web_origins         = local.web_origins
  deletion_protection = var.protect_resources
}

module "api" {
  source               = "../../modules/api"
  name                 = local.name
  image_tag            = var.image_tag
  data_source          = var.data_source
  strategies           = var.strategies
  cognito_user_pool_id = module.auth.user_pool_id
  cognito_client_id    = module.auth.client_id
  log_retention_days   = var.log_retention_days
  force_delete_images  = !var.protect_resources
}

module "ingest" {
  source               = "../../modules/ingest"
  name                 = local.name
  ingest_function_arn  = module.api.ingest_function_arn
  ingest_function_name = module.api.ingest_function_name
}

module "web" {
  source            = "../../modules/web"
  name              = local.name
  api_function_url  = module.api.api_function_url
  api_function_name = module.api.api_function_name
  force_destroy     = !var.protect_resources
}

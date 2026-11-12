data "aws_region" "current" {}

# Cognito per docs/auth-contract.md: invite-only, PKCE public client, groups engineers and households.

resource "aws_cognito_user_pool" "this" {
  name                     = var.name
  alias_attributes         = ["email"]
  auto_verified_attributes = ["email"]
  deletion_protection      = var.deletion_protection ? "ACTIVE" : "INACTIVE"

  username_configuration {
    case_sensitive = false
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_user_group" "engineers" {
  name         = "engineers"
  user_pool_id = aws_cognito_user_pool.this.id
  description  = "See the risk map, transformer cards and outage detail"
}

resource "aws_cognito_user_group" "households" {
  name         = "households"
  user_pool_id = aws_cognito_user_pool.this.id
  description  = "See their own household usage only"
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${var.name}-web"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret                      = false # public SPA client: authorization code + PKCE
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors        = "ENABLED"
  enable_token_revocation              = true

  callback_urls = [for origin in var.web_origins : "${origin}/auth/callback"]
  logout_urls   = [for origin in var.web_origins : "${origin}/"]

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30
  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

# Managed login (version 2): the newer Cognito sign-in pages. Cognito creates a default style for the
# web client when the domain switches to version 2; it is managed outside Terraform for now.
resource "aws_cognito_user_pool_domain" "this" {
  domain                = var.domain_prefix
  user_pool_id          = aws_cognito_user_pool.this.id
  managed_login_version = 2
}

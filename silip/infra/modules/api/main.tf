# API and ingest Lambdas from one container image, the database secret, and least-privilege roles.
# The function URL uses AWS_IAM auth; only CloudFront (OAC, web module) may call it.

data "aws_region" "current" {}

locals {
  functions = {
    api    = { command = "silip.app.handler", memory = var.api_memory_mb, timeout = 30 }
    ingest = { command = "silip.ingest.handler.handle", memory = 256, timeout = 10 }
  }
}

resource "aws_ecr_repository" "api" {
  name                 = var.name
  image_tag_mutability = "IMMUTABLE"
  force_delete         = var.force_delete_images

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Empty on purpose: the Neon project already exists, and its URL is put in by hand so it never
# lands in Terraform state. aws secretsmanager put-secret-value --secret-id <arn> --secret-string ...
resource "aws_secretsmanager_secret" "database_url" {
  name                    = "${var.name}/database-url"
  description             = "Neon pooled connection URI for SILIP Lambdas"
  recovery_window_in_days = var.secret_recovery_days
}

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "function" {
  for_each           = local.functions
  name               = "${var.name}-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

resource "aws_cloudwatch_log_group" "function" {
  for_each          = local.functions
  name              = "/aws/lambda/${var.name}-${each.key}"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "function" {
  for_each = local.functions

  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.function[each.key].arn}:*"]
  }

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.database_url.arn]
  }
}

resource "aws_iam_role_policy" "function" {
  for_each = local.functions
  name     = "${var.name}-${each.key}"
  role     = aws_iam_role.function[each.key].id
  policy   = data.aws_iam_policy_document.function[each.key].json
}

resource "aws_lambda_function" "function" {
  for_each      = local.functions
  function_name = "${var.name}-${each.key}"
  role          = aws_iam_role.function[each.key].arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:${var.image_tag}"
  architectures = [var.architecture]
  memory_size   = each.value.memory
  timeout       = each.value.timeout

  image_config {
    command = [each.value.command]
  }

  environment {
    variables = merge(var.strategies, {
      DATA_SOURCE          = var.data_source
      DATABASE_SECRET_ARN  = aws_secretsmanager_secret.database_url.arn
      COGNITO_REGION       = data.aws_region.current.region
      COGNITO_USER_POOL_ID = var.cognito_user_pool_id
      COGNITO_CLIENT_ID    = var.cognito_client_id
    })
  }

  depends_on = [aws_cloudwatch_log_group.function, aws_iam_role_policy.function]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.function["api"].function_name
  authorization_type = "AWS_IAM"
}

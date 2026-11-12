# API and scoring Lambdas from one container image, the database secret, and least-privilege roles.
# The API Lambda also receives device HTTPS readings (no IoT Core ingest Lambda).
# The function URL uses AWS_IAM auth; only CloudFront (OAC, web module) may call it.
# Scoring is one more entry in local.functions, not a new module: it shares the image, secret, env
# and per-function role/log-group pattern, so a module would only duplicate that wiring.

data "aws_region" "current" {}

locals {
  functions = {
    api = { command = "silip.app.handler", memory = var.api_memory_mb, timeout = 30, reserved = null }
    # Writes risk scores to Neon on a schedule. No reserved concurrency: this account's Lambda limit is 10,
    # and AWS refuses any reservation that leaves fewer than 10 unreserved. Runs are idempotent per
    # 15-minute bucket (score_run), so a rare overlap repeats work but never double-writes.
    # Timeout is the Lambda max; measured 34 s at 2,000 transformers with lightgbm, so a 30 s weather
    # fetch budget (ADR 0006) still fits with wide margin.
    score = { command = "silip.scoring.handler.handle", memory = var.scoring_memory_mb, timeout = 900, reserved = null }
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

  # null leaves api and ingest unreserved.
  reserved_concurrent_executions = each.value.reserved

  image_config {
    command = [each.value.command]
  }

  environment {
    variables = merge(var.strategies, {
      DATA_SOURCE          = var.data_source
      WEATHER_SOURCE       = var.weather_source
      OPEN_METEO_BASE_URL  = var.open_meteo_base_url
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

# Every var.scoring_schedule, EventBridge invokes the score Lambda; the API only reads stored scores.
resource "aws_cloudwatch_event_rule" "score" {
  name                = "${var.name}-score"
  description         = "Invoke the SILIP scoring Lambda"
  schedule_expression = var.scoring_schedule
}

resource "aws_cloudwatch_event_target" "score" {
  rule = aws_cloudwatch_event_rule.score.name
  arn  = aws_lambda_function.function["score"].arn
}

# A tick that cannot start (previous run still going, reserved concurrency 1) or a run that fails
# is dropped, not retried: the next tick scores the newest data anyway.
resource "aws_lambda_function_event_invoke_config" "score" {
  function_name                = aws_lambda_function.function["score"].function_name
  maximum_retry_attempts       = 0
  maximum_event_age_in_seconds = 900
}

resource "aws_lambda_permission" "score_schedule" {
  statement_id  = "AllowEventBridgeSchedule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.function["score"].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.score.arn
}

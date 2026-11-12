# API, mobile-PoC and scoring Lambdas share one container image and database secret, with separate
# execution roles and handlers. Function URLs use AWS_IAM; CloudFront OAC is the caller.

data "aws_region" "current" {}

locals {
  functions = {
    api    = { command = "silip.app.handler", memory = var.api_memory_mb, timeout = 30, reserved = null }
    mobile = { command = "silip.mobile.handler", memory = 512, timeout = 15, reserved = null }
    # Writes risk scores to Neon on a schedule. No reserved concurrency: this account's Lambda limit is 10,
    # and AWS refuses any reservation that leaves fewer than 10 unreserved. Runs are idempotent per
    # 15-minute bucket (score_run), so a rare overlap repeats work but never double-writes.
    # Timeout is the Lambda max; measured 34 s at 2,000 transformers with lightgbm.
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

  # null leaves the request handlers and scoring function unreserved.
  reserved_concurrent_executions = each.value.reserved

  image_config {
    command = [each.value.command]
  }

  environment {
    variables = merge(var.strategies, {
      DATA_SOURCE           = var.data_source
      DATABASE_SECRET_ARN   = aws_secretsmanager_secret.database_url.arn
      MOBILE_POC_DEVICE_IDS = join(",", var.mobile_poc_device_ids)
      COGNITO_REGION        = data.aws_region.current.region
      COGNITO_USER_POOL_ID  = var.cognito_user_pool_id
      COGNITO_CLIENT_ID     = var.cognito_client_id
    })
  }

  depends_on = [aws_cloudwatch_log_group.function, aws_iam_role_policy.function]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.function["api"].function_name
  authorization_type = "AWS_IAM"
}

resource "aws_lambda_function_url" "mobile" {
  function_name      = aws_lambda_function.function["mobile"].function_name
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

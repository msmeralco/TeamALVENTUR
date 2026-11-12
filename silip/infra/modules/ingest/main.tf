# AWS IoT Core: devices publish readings over MQTT; a topic rule hands each one to the ingest Lambda.
# Things and certificates are created per node at install time, not here.

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  iot_arn = "arn:aws:iot:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}"
}

resource "aws_iot_topic_rule" "readings" {
  name        = replace("${var.name}_readings", "-", "_")
  enabled     = true
  sql         = "SELECT * FROM 'silip/v1/+/+/reading'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = var.ingest_function_arn
  }
}

resource "aws_lambda_permission" "iot" {
  statement_id  = "AllowIotTopicRule"
  action        = "lambda:InvokeFunction"
  function_name = var.ingest_function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.readings.arn
}

# Attach to each node's certificate. A node may connect only as its own thing and publish only readings.
resource "aws_iot_policy" "node" {
  name = "${var.name}-node"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "iot:Connect"
        Resource = "${local.iot_arn}:client/$${iot:Connection.Thing.ThingName}"
      },
      {
        Effect   = "Allow"
        Action   = "iot:Publish"
        Resource = "${local.iot_arn}:topic/silip/v1/*/*/reading"
      },
    ]
  })
}

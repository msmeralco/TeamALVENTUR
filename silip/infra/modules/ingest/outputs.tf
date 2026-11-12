output "node_policy_name" {
  description = "IoT policy to attach to each clamp node's certificate."
  value       = aws_iot_policy.node.name
}

output "topic_rule_name" {
  description = "IoT topic rule that forwards readings to the ingest Lambda."
  value       = aws_iot_topic_rule.readings.name
}

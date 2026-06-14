# CloudWatch: per-scanner log group and failed-invocation alarm.
resource "aws_cloudwatch_log_group" "scanner" {
  for_each = local.enabled_scanner_jobs

  name              = "/ecs/${local.name_prefix}/${each.key}"
  retention_in_days = var.log_retention_in_days
  tags              = merge(local.common_tags, { Scanner = each.key })
}

resource "aws_cloudwatch_metric_alarm" "eventbridge_failed_invocations" {
  for_each = var.scanner_jobs

  alarm_name          = "${local.name_prefix}-${each.key}-failed-invocations"
  alarm_description   = "Alarm when EventBridge fails to invoke ${each.key} scanner task."
  namespace           = "AWS/Events"
  metric_name         = "FailedInvocations"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"

  dimensions = {
    RuleName = aws_cloudwatch_event_rule.scanner[each.key].name
  }

  alarm_actions = local.alarm_topic_arn != null ? [local.alarm_topic_arn] : []
  ok_actions    = local.alarm_topic_arn != null ? [local.alarm_topic_arn] : []

  tags = merge(local.common_tags, { Scanner = each.key })
}

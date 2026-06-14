# SNS: alarm topic, email subscriptions, and task-failure notifications.
resource "aws_sns_topic" "alarms" {
  count = local.create_alarm_topic ? 1 : 0

  name = "${local.name_prefix}-alarms"
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "alarm_emails" {
  for_each = local.create_alarm_topic ? toset(var.alarm_notification_emails) : toset([])

  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = each.value
}

# Allow EventBridge to publish task-failure events to the topic.
data "aws_iam_policy_document" "alarms_topic" {
  count = local.create_alarm_topic ? 1 : 0

  statement {
    sid       = "AllowEventBridgePublish"
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alarms[0].arn]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_sns_topic_policy" "alarms" {
  count = local.create_alarm_topic ? 1 : 0

  arn    = aws_sns_topic.alarms[0].arn
  policy = data.aws_iam_policy_document.alarms_topic[0].json
}

# Notify when a scanner ECS task fails to start (image pull error, resource issues, etc).
resource "aws_cloudwatch_event_rule" "task_failed_to_start" {
  count = local.create_alarm_topic ? 1 : 0

  name        = "${local.name_prefix}-task-failed-to-start"
  description = "Detect scanner ECS tasks that fail to start."

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Task State Change"]
    detail = {
      clusterArn = [aws_ecs_cluster.scanner.arn]
      lastStatus = ["STOPPED"]
      stopCode   = ["TaskFailedToStart"]
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "task_failed_to_start_sns" {
  count = local.create_alarm_topic ? 1 : 0

  rule      = aws_cloudwatch_event_rule.task_failed_to_start[0].name
  target_id = "task-failed-to-start-sns"
  arn       = aws_sns_topic.alarms[0].arn

  input_transformer {
    input_paths = {
      task    = "$.detail.taskArn"
      group   = "$.detail.group"
      reason  = "$.detail.stoppedReason"
      cluster = "$.detail.clusterArn"
    }
    input_template = "\"Scanner ECS task failed to start. Cluster: <cluster> | Group: <group> | Task: <task> | Reason: <reason>\""
  }
}

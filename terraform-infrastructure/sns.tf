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

resource "aws_cloudwatch_event_rule" "scanner_task_completed" {
  for_each = local.create_alarm_topic ? local.enabled_scanner_jobs : {}

  name        = "${local.name_prefix}-${each.key}-task-completed"
  description = "Detect when ${each.key} scanner ECS task stops after running."

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Task State Change"]
    detail = {
      clusterArn = [aws_ecs_cluster.scanner.arn]
      lastStatus = ["STOPPED"]
      stopCode   = ["EssentialContainerExited"]
      group      = ["family:${aws_ecs_task_definition.scanner[each.key].family}"]
    }
  })

  tags = merge(local.common_tags, { Scanner = each.key })
}

resource "aws_cloudwatch_event_target" "scanner_task_completed_sns" {
  for_each = local.create_alarm_topic ? local.enabled_scanner_jobs : {}

  rule      = aws_cloudwatch_event_rule.scanner_task_completed[each.key].name
  target_id = "${each.key}-task-completed-sns"
  arn       = aws_sns_topic.alarms[0].arn

  input_transformer {
    input_paths = {
      task     = "$.detail.taskArn"
      group    = "$.detail.group"
      reason   = "$.detail.stoppedReason"
      exitCode = "$.detail.containers[0].exitCode"
    }
    input_template = "\"Scanner ${each.key} finished. Exit code: <exitCode> (0=success) | Group: <group> | Task: <task> | Reason: <reason>\""
  }
}

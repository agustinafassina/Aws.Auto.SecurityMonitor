resource "aws_cloudwatch_event_rule" "scanner" {
  for_each = var.scanner_jobs

  name                = "${local.name_prefix}-${each.key}-schedule"
  description         = "Schedule for ${each.key} scanner task."
  schedule_expression = each.value.schedule_expression
  state               = each.value.enabled ? "ENABLED" : "DISABLED"
  tags                = merge(local.common_tags, { Scanner = each.key })
}

resource "aws_cloudwatch_event_target" "scanner_ecs" {
  for_each = local.enabled_scanner_jobs

  rule      = aws_cloudwatch_event_rule.scanner[each.key].name
  target_id = "${each.key}-ecs-target"
  arn       = aws_ecs_cluster.scanner.arn
  role_arn  = aws_iam_role.eventbridge_invoke_ecs.arn

  ecs_target {
    task_count          = 1
    launch_type         = "FARGATE"
    task_definition_arn = aws_ecs_task_definition.scanner[each.key].arn
    platform_version    = "LATEST"

    network_configuration {
      subnets          = local.selected_subnet_ids
      security_groups  = [aws_security_group.ecs_tasks.id]
      assign_public_ip = var.assign_public_ip
    }
  }
}

output "ecs_cluster_name" {
  description = "ECS cluster name for scanner tasks."
  value       = aws_ecs_cluster.scanner.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN for scanner tasks."
  value       = aws_ecs_cluster.scanner.arn
}

output "ecr_repository_urls" {
  description = "ECR repository URLs keyed by scanner name."
  value = {
    for scanner_name, repository in aws_ecr_repository.scanner :
    scanner_name => repository.repository_url
  }
}

output "task_definition_arns" {
  description = "ECS task definition ARNs keyed by scanner name."
  value = {
    for scanner_name, task_definition in aws_ecs_task_definition.scanner :
    scanner_name => task_definition.arn
  }
}

output "eventbridge_rule_names" {
  description = "EventBridge rule names keyed by scanner name."
  value = {
    for scanner_name, rule in aws_cloudwatch_event_rule.scanner :
    scanner_name => rule.name
  }
}

output "cloudwatch_log_group_names" {
  description = "CloudWatch log group names keyed by scanner name."
  value = {
    for scanner_name, log_group in aws_cloudwatch_log_group.scanner :
    scanner_name => log_group.name
  }
}

output "alarm_sns_topic_arn" {
  description = "SNS topic ARN used for scanner alarm notifications (null when none configured)."
  value       = local.alarm_topic_arn
}

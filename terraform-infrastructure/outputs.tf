output "name_prefix" {
  description = "Resource name prefix: tf-{environment}-{project_name}."
  value       = local.name_prefix
}

output "ecs_cluster_name" {
  description = "ECS cluster name for scanner tasks."
  value       = aws_ecs_cluster.scanner.name
}

output "ecr_repository_url" {
  description = "ECR repository URL for all scanner images."
  value       = aws_ecr_repository.scanners.repository_url
}

output "findings_s3_bucket" {
  description = "S3 bucket name where scanner findings are stored."
  value       = aws_s3_bucket.findings.id
}

output "task_definition_families" {
  description = "ECS task definition family names keyed by scanner (for run-task / Azure DevOps ops pipelines)."
  value = {
    for scanner_name, task_definition in aws_ecs_task_definition.scanner :
    scanner_name => task_definition.family
  }
}

output "eventbridge_rule_names" {
  description = "EventBridge schedule rule names keyed by scanner (for enable/disable schedule)."
  value = {
    for scanner_name, rule in aws_cloudwatch_event_rule.scanner :
    scanner_name => rule.name
  }
}

output "ecs_subnet_ids" {
  description = "Subnet IDs used by ECS Fargate tasks."
  value       = local.selected_subnet_ids
}

output "ecs_security_group_id" {
  description = "Security group ID used by ECS Fargate tasks."
  value       = aws_security_group.ecs_tasks.id
}

output "alarm_sns_topic_arn" {
  description = "SNS topic ARN for scanner notifications (null when none configured)."
  value       = local.alarm_topic_arn
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN."
  value       = aws_ecs_cluster.scanner.arn
}

output "task_definition_arns" {
  description = "ECS task definition ARNs keyed by scanner name."
  value = {
    for scanner_name, task_definition in aws_ecs_task_definition.scanner :
    scanner_name => task_definition.arn
  }
}

output "cloudwatch_log_group_names" {
  description = "CloudWatch log group names keyed by scanner name."
  value = {
    for scanner_name, log_group in aws_cloudwatch_log_group.scanner :
    scanner_name => log_group.name
  }
}
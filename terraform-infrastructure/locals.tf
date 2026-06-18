locals {
  name_prefix = "tf-${var.environment}-${var.project_name}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.project_tag != "" ? { CostCenter = var.project_tag } : {},
    var.tags
  )

  selected_vpc_id     = var.vpc_id != null ? var.vpc_id : data.aws_vpc.default[0].id
  selected_subnet_ids = length(var.subnet_ids) > 0 ? var.subnet_ids : data.aws_subnets.selected[0].ids

  enabled_scanner_jobs = {
    for scanner_name, scanner_config in var.scanner_jobs :
    scanner_name => scanner_config if scanner_config.enabled
  }

  create_alarm_topic = length(var.alarm_notification_emails) > 0
  alarm_topic_arn    = local.create_alarm_topic ? aws_sns_topic.alarms[0].arn : var.alarm_sns_topic_arn
}
variable "aws_region" {
  description = "AWS region where resources are deployed."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used as prefix for resources."
  type        = string
  default     = "aws-auto-security-monitor"
}

variable "environment" {
  description = "Environment name (e.g. dev, stg, prod)."
  type        = string
  default     = "dev"
}

variable "default_image_tag" {
  description = "Default Docker tag to use in ECS tasks when scanner doesn't set one."
  type        = string
  default     = "latest"
}

variable "vpc_id" {
  description = "VPC ID for ECS tasks. If null, the default VPC is used."
  type        = string
  default     = null
}

variable "subnet_ids" {
  description = "Subnets for ECS tasks. If empty, all subnets from selected/default VPC are used."
  type        = list(string)
  default     = []
}

variable "assign_public_ip" {
  description = "Whether Fargate tasks receive a public IP."
  type        = bool
  default     = true
}

variable "log_retention_in_days" {
  description = "CloudWatch log retention for ECS task logs."
  type        = number
  default     = 14
}

variable "alarm_sns_topic_arn" {
  description = "Optional pre-existing SNS topic ARN for alarms. Ignored when alarm_notification_emails is set (a topic is created instead)."
  type        = string
  default     = null
}

variable "alarm_notification_emails" {
  description = "Email addresses to notify on scanner failures. When non-empty, an SNS topic is created and each email is subscribed."
  type        = list(string)
  default     = []
}

variable "ecr_force_delete" {
  description = "Whether ECR repositories can be deleted even if images exist."
  type        = bool
  default     = true
}

variable "scanner_jobs" {
  description = "Map of scanner jobs. Add new entries to scale with more containers."
  type = map(object({
    schedule_expression = string
    cpu                 = number
    memory              = number
    command             = optional(list(string), ["--source", "aws"])
    image_tag           = optional(string, null)
    enabled             = optional(bool, true)
  }))

  default = {
    route53 = {
      schedule_expression = "rate(1 day)"
      cpu                 = 256
      memory              = 512
      command             = ["--source", "aws"]
    }
    rds = {
      schedule_expression = "rate(1 day)"
      cpu                 = 256
      memory              = 512
      command             = ["--source", "aws"]
    }
  }
}

variable "tags" {
  description = "Additional tags applied to all resources."
  type        = map(string)
  default     = {}
}

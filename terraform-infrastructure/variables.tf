variable "aws_region" {
  description = "AWS region where resources are deployed."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d+$", var.aws_region))
    error_message = "aws_region must be a valid AWS region identifier (e.g. sa-east-1)."
  }
}

variable "project_name" {
  description = "Project slug used in resource names and tags. Lowercase, descriptive, no generic names."
  type        = string
  default     = "security-scan"

  validation {
    condition = (
      can(regex("^[a-z][a-z0-9-]{2,31}$", var.project_name))
      && !contains(["test", "temp", "tmp", "resource1", "default"], var.project_name)
    )
    error_message = "project_name must be 3-32 chars (lowercase letters, numbers, hyphens) and not a generic placeholder."
  }
}

variable "project_tag" {
  description = "Optional cost-allocation tag value applied to all resources (empty to disable)."
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment. Included in resource names and state key."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "qa", "stg", "prod"], var.environment)
    error_message = "environment must be one of: dev, qa, stg, prod."
  }
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

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_in_days)
    error_message = "log_retention_in_days must be a valid CloudWatch Logs retention value."
  }
}

variable "alarm_sns_topic_arn" {
  description = "Optional pre-existing SNS topic ARN for alarms. Ignored when alarm_notification_emails is set (a topic is created instead)."
  type        = string
  default     = null
  sensitive   = true
}

variable "alarm_notification_emails" {
  description = "Email addresses for SNS notifications (task failures, scan completion, EventBridge alarms). When non-empty, an SNS topic is created and each email is subscribed."
  type        = list(string)
  default     = []
  sensitive   = true
}

variable "ecr_force_delete" {
  description = "Whether ECR repositories can be deleted even if images exist."
  type        = bool
  default     = true
}

variable "ecr_untagged_image_expiration_days" {
  description = "Delete untagged ECR images older than this many days (leftover digests after module tag overwrites)."
  type        = number
  default     = 7

  validation {
    condition     = var.ecr_untagged_image_expiration_days >= 1
    error_message = "ecr_untagged_image_expiration_days must be at least 1."
  }
}

variable "ecr_max_image_count" {
  description = "Maximum number of images to retain in the scanners ECR repo (tagged and untagged combined)."
  type        = number
  default     = 5

  validation {
    condition     = var.ecr_max_image_count >= 1
    error_message = "ecr_max_image_count must be at least 1."
  }
}

variable "scanner_jobs" {
  description = "Map of scanner jobs. Add new entries to scale with more containers."
  type = map(object({
    schedule_expression = string
    cpu                 = number
    memory              = number
    command             = optional(list(string))
    image_tag           = optional(string)
    enabled             = optional(bool, true)
  }))

  default = {
    route53 = {
      schedule_expression = "rate(1 day)"
      cpu                 = 256
      memory              = 512
      command             = ["python", "route53/scan_route53.py", "--source", "aws"]
    }
  }

  validation {
    condition     = length(var.scanner_jobs) > 0
    error_message = "scanner_jobs must contain at least one scanner."
  }
}

variable "findings_s3_prefix_base" {
  description = "Base S3 prefix for findings (each scanner appends its key, e.g. findings/route53)."
  type        = string
  default     = "findings"
}

variable "tags" {
  description = "Additional tags applied to all resources (merged with Project, Environment, ManagedBy)."
  type        = map(string)
  default     = {}
}

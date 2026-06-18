data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task_execution" {
  name               = "${local.name_prefix}-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_managed" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name               = "${local.name_prefix}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "ecs_task_permissions" {
  statement {
    sid = "AllowRoute53ReadOnlyDiscovery"
    actions = [
      "route53:ListHostedZones",
      "route53:GetDNSSEC",
      "route53:ListQueryLoggingConfigs",
    ]
    resources = ["*"]
  }

  statement {
    sid = "AllowFindingsUpload"
    actions = [
      "s3:PutObject"
    ]
    resources = ["${aws_s3_bucket.findings.arn}/*"]
  }
}

resource "aws_iam_policy" "ecs_task_permissions" {
  name   = "${local.name_prefix}-ecs-task-policy"
  policy = data.aws_iam_policy_document.ecs_task_permissions.json
  tags   = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_custom_permissions" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task_permissions.arn
}

data "aws_iam_policy_document" "eventbridge_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eventbridge_invoke_ecs" {
  name               = "${local.name_prefix}-eventbridge-ecs-invoke-role"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "eventbridge_invoke_ecs" {
  statement {
    sid = "RunScannerTasks"
    actions = [
      "ecs:RunTask"
    ]
    resources = [for scanner_name, task_def in aws_ecs_task_definition.scanner : task_def.arn]
  }

  statement {
    sid = "PassTaskRoles"
    actions = [
      "iam:PassRole"
    ]
    resources = [
      aws_iam_role.ecs_task_execution.arn,
      aws_iam_role.ecs_task.arn
    ]
  }

  statement {
    sid = "DescribeClusterAndTasks"
    actions = [
      "ecs:DescribeTasks",
      "ecs:DescribeTaskDefinition"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "eventbridge_invoke_ecs" {
  name   = "${local.name_prefix}-eventbridge-ecs-invoke-policy"
  policy = data.aws_iam_policy_document.eventbridge_invoke_ecs.json
  tags   = local.common_tags
}

resource "aws_iam_role_policy_attachment" "eventbridge_invoke_ecs" {
  role       = aws_iam_role.eventbridge_invoke_ecs.name
  policy_arn = aws_iam_policy.eventbridge_invoke_ecs.arn
}

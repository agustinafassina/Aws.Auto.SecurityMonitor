resource "aws_ecs_cluster" "scanner" {
  name = "${local.name_prefix}-cluster"
  tags = local.common_tags
}

resource "aws_ecs_task_definition" "scanner" {
  for_each = local.enabled_scanner_jobs

  family                   = "${local.name_prefix}-${each.key}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(each.value.cpu)
  memory                   = tostring(each.value.memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "${each.key}-scanner"
      image     = "${aws_ecr_repository.scanners.repository_url}:${coalesce(each.value.image_tag, each.key)}"
      essential = true
      command   = each.value.command

      environment = [
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "FINDINGS_S3_BUCKET"
          value = aws_s3_bucket.findings.id
        },
        {
          name  = "FINDINGS_S3_PREFIX"
          value = "${var.findings_s3_prefix_base}/${each.key}"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.scanner[each.key].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, { Scanner = each.key })
}

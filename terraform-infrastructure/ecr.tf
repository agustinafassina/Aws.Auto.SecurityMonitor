# ECR: one image repository per scanner module.
resource "aws_ecr_repository" "scanner" {
  for_each = local.enabled_scanner_jobs

  name                 = "${var.project_name}/${each.key}"
  image_tag_mutability = "MUTABLE"
  force_delete         = var.ecr_force_delete

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, { Scanner = each.key })
}

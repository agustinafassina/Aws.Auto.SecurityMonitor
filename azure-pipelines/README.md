# 🔄 Azure DevOps Pipelines
Build, deploy, and operate scanners on AWS. Infra details: [terraform-infrastructure/README.md](../terraform-infrastructure/README.md).

## 📋 Pipelines
| Pipeline | File | Trigger |
|----------|------|---------|
| Route53 build | `modules/route53-build.yml` | `scan-resources/route53/**` + shared files on `main` |
| Route53 ops | `modules/route53-ops.yml` | Manual |
| Terraform | `infrastructure.yml` | `terraform-infrastructure/**` on `main` |

Templates: `templates/module-build-steps.yml`, `templates/module-ops-steps.yml`

## ⚙️ One-time setup
1. 🔑 AWS service connection: `aws-security-monitor`
2. 📦 Variable group `aws-security-monitor-dev` — [variable-group.example.md](variable-group.example.md)
3. ✅ Azure environment `security-monitor-dev` (approval before Terraform apply)
4. 📌 Register the three YAML files as pipelines

## 🚀 Route53 flow
1. 📝 Code change under `scan-resources/route53/` → **route53-build** (AWS login → ECR login → build → push tag `route53`)
2. ▶️ **route53-ops** (manual):

| Action | Effect |
|--------|--------|
| `run-now` | `ecs run-task` (same task def as schedule) |
| `enable-schedule` | Enable EventBridge rule |
| `disable-schedule` | Disable EventBridge rule |

3. 🏗️ Infra change → **infrastructure** (`init -backend-config` → `plan` → `apply tfplan`)

## ➕ New module pipelines
Copy `scan-resources/_template/azure-pipelines-*.example` → `modules/<module>-build.yml` and `<module>-ops.yml`. Add variable group keys `ECS_TASK_FAMILY_<MODULE>`, `EVENTBRIDGE_RULE_<MODULE>`.

Full module checklist: [_template/README.md](../scan-resources/_template/README.md).

## 🐳 Images
Single ECR repo (`ecrRepository` in variable group). One tag per module (`route53`, …).

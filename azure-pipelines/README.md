# 🔄 Azure DevOps Pipelines
Build, deploy, and operate scanners on AWS. Infra: [terraform-infrastructure/README.md](../terraform-infrastructure/README.md).

## 📋 Pipelines (register 3 in Azure DevOps)

| Pipeline | File | Trigger |
|----------|------|---------|
| **Scanners build** | `scanners-build.yml` | `scan-resources/**` on `main` (all modules in matrix) |
| **Scanners ops** | `scanners-ops.yml` | Manual |
| **Terraform** | `infrastructure.yml` | `terraform-infrastructure/**` on `main` |

Shared templates: `templates/module-build-steps.yml`, `templates/module-ops-steps.yml`

## ⚙️ One-time setup
1. 🔑 AWS service connection: `aws-security-monitor`
2. 📦 Variable group `aws-security-monitor-dev` — [variable-group.example.md](variable-group.example.md)
3. ✅ Environment `security-monitor-dev` (Terraform apply approval)
4. 📌 Register `scanners-build.yml`, `scanners-ops.yml`, `infrastructure.yml`

## 🐳 Build all images (`scanners-build.yml`)
- **One pipeline** builds **every module** in the `strategy.matrix` (parallel jobs).
- Today: `route53`. Change in `scanner_core.py` rebuilds all matrix entries.
- Per module: smoke test → AWS login → ECR login → docker build → push `ECR:{module}`.

## ▶️ On-demand / EventBridge (`scanners-ops.yml`)
Single manual pipeline. Parameters:

| Parameter | Values |
|-----------|--------|
| `scanner` | `route53`, … |
| `action` | `run-now`, `enable-schedule`, `disable-schedule` |

| Action | Effect |
|--------|--------|
| `run-now` | `ecs run-task` (same task def as schedule) |
| `enable-schedule` | Enable EventBridge rule |
| `disable-schedule` | Disable EventBridge rule |

Task family and rule name are derived from `namePrefix` + module (no per-module variable group keys).

## 🏗️ Infrastructure (`infrastructure.yml`)
`init -backend-config` → `plan -out=tfplan` → `apply tfplan`

## ➕ Add a new module (2 edits)
1. **`scanners-build.yml`** — add matrix row:
   ```yaml
   s3:
     moduleName: s3
   ```
2. **`scanners-ops.yml`** — add `s3` to `parameters.scanner.values`

Then follow [scan-resources/_template/README.md](../scan-resources/_template/README.md) for code, Terraform, and IAM.

No new pipeline YAML files per module.

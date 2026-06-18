# 📘 AWS Auto Security Monitor
Route53 security scanning on AWS — containerized Python jobs, scheduled or on-demand via ECS Fargate.

## 🗺️ Workflow
![Overview](./workflow.svg)

## 📂 Repository map
| Path | README | Scope |
|------|--------|--------|
| `scan-resources/` | [scan-resources/README.md](scan-resources/README.md) | Python scanners, `scanner_core`, Route53 module |
| `scan-resources/_template/` | [_template/README.md](scan-resources/_template/README.md) | Scaffold a new scanner module (end-to-end) |
| `terraform-infrastructure/` | [terraform-infrastructure/README.md](terraform-infrastructure/README.md) | AWS infra (ECS, ECR, EventBridge, S3, SNS, IAM) |
| `terraform-infrastructure/environments/` | [environments/README.md](terraform-infrastructure/environments/README.md) | Per-env `tfvars` and backend config |
| `azure-pipelines/` | [azure-pipelines/README.md](azure-pipelines/README.md) | `scanners-build`, `scanners-ops`, `infrastructure` |
| `scripts/` | — | `run-scanner.sh`, `scanner-schedule.sh` (see terraform README) |

## ▶️ Quick start
1. 🏗️ Deploy infra → [terraform-infrastructure/README.md](terraform-infrastructure/README.md) (prerequisite: [environments/](terraform-infrastructure/environments/README.md))
2. 🔄 Build images → [azure-pipelines/scanners-build.yml](azure-pipelines/scanners-build.yml)
3. 🐍 Run locally → [scan-resources/README.md](scan-resources/README.md)

On-demand / schedule: [azure-pipelines/scanners-ops.yml](azure-pipelines/scanners-ops.yml)

## 📌 Active module
**route53** — scans hosted zones (DNSSEC, query logging). Max 10 domains per run.

## ➕ Add modules later
[scan-resources/_template/README.md](scan-resources/_template/README.md)

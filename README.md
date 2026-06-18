# 📘 AWS Auto Security Monitor
A **modular** security-scanning platform for AWS. Each scanner is a self-contained Python module shipped as a container and run on ECS Fargate — scheduled (EventBridge) or on-demand. Add new scanners without touching the platform: drop a module in `scan-resources/`, add one `scanner_jobs` entry, and add it to the build matrix.

## 🗺️ Workflow
![Overview](./workflow.svg)

## 📂 Repository map
| Path | README | Scope |
|------|--------|--------|
| `scan-resources/` | [scan-resources/README.md](scan-resources/README.md) | Scanner modules + shared `scanner_core` check engine |
| `scan-resources/_template/` | [_template/README.md](scan-resources/_template/README.md) | Scaffold a new scanner module (end-to-end) |
| `terraform-infrastructure/` | [terraform-infrastructure/README.md](terraform-infrastructure/README.md) | Shared AWS platform (ECS, ECR, EventBridge, S3, SNS, IAM); per-module resources via `scanner_jobs` |
| `terraform-infrastructure/environments/` | [environments/README.md](terraform-infrastructure/environments/README.md) | Per-env `tfvars` and backend config |
| `azure-pipelines/` | [azure-pipelines/README.md](azure-pipelines/README.md) | `scanners-build` (matrix), `scanners-ops`, `infrastructure` |
| `scripts/` | — | `run-scanner.sh`, `scanner-schedule.sh` (see terraform README) |

## ▶️ Quick start
1. 🏗️ Deploy infra → [terraform-infrastructure/README.md](terraform-infrastructure/README.md) (prerequisite: [environments/](terraform-infrastructure/environments/README.md))
2. 🔄 Build images → [azure-pipelines/scanners-build.yml](azure-pipelines/scanners-build.yml)
3. 🐍 Run locally → [scan-resources/README.md](scan-resources/README.md)

On-demand / schedule: [azure-pipelines/scanners-ops.yml](azure-pipelines/scanners-ops.yml)

## 🧩 How a module works
Each module is independent and follows the same contract:

1. **Code** — a `scan-resources/<module>/` package with its own `Dockerfile`, reusing the shared `scanner_core` check engine.
2. **Image** — one ECR repo, one tag per module (`scanners:<module>`), built by the `scanners-build` matrix.
3. **Run** — a `scanner_jobs` entry creates its ECS task definition, EventBridge schedule, log group, and SNS notifications.
4. **Output** — findings are pushed to S3 (`findings/<module>/…`) and failures/completions notify via SNS.

## 📋 Modules
| Module | Scope | Status |
|--------|-------|--------|
| `route53` | Hosted zones — DNSSEC, query logging (max 10 domains/run) | ✅ Active |
| _your next module_ | … | Add via the template |

## ➕ Add a module
End-to-end guide (code → Terraform → IAM → pipelines): [scan-resources/_template/README.md](scan-resources/_template/README.md)

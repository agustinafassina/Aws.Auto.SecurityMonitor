# 📘 AWS Auto Security Monitor
Scalable baseline to scan AWS resources with containerized Python jobs and recurring execution on AWS.

## 🗺️ Workflow
High-level overview of how the two sections connect. See each section README for the detailed diagrams.

![AWS Auto Security Monitor Workflow](./workflow.svg)

## 🧱 Repository Structure
- `scan-resources/`: scanner modules (each with its own `Dockerfile`), shared `scanner_core.py`
- `terraform-infrastructure/`: ECS, ECR, EventBridge, CloudWatch, S3, IAM
- `azure-pipelines/`: per-module build/ops pipelines + shared infrastructure pipeline
- `scripts/`: `run-scanner.sh`, `scanner-schedule.sh`

## ▶️ Getting Started
Use the module-specific documentation to run commands and deploy:

- `scan-resources/README.md` for scanner execution and module creation.
- `terraform-infrastructure/README.md` for Terraform and AWS operations.
- `azure-pipelines/README.md` for CI/CD setup.

> Prerequisite: create the Terraform state S3 bucket and configure `terraform-infrastructure/backend.tf` before `terraform init`.

## 📈 Scaling Model
Add a scanner module:

1. `scan-resources/<service>/scan_<service>.py` + `json-example/example.json`
2. Entry in `terraform-infrastructure/terraform.tfvars` → `scanner_jobs`
3. `azure-pipelines/modules/<service>-build.yml` + `<service>-ops.yml`
4. Build and push image with module tag → Fargate pulls it on next run (no terraform apply for code-only changes)

One ECR repo; each module uses its own tag (`route53`, `rds`, …).

## 📚 Module Documentation
- Scanning framework: `scan-resources/README.md`
- Infrastructure: `terraform-infrastructure/README.md`
- Pipelines: `azure-pipelines/README.md`

## 📝 Notes
- Scanner scripts support `--source aws|file|auto`.
- AWS discovery uses `boto3` and IAM roles (no API keys).
- Manual ops per module: Azure DevOps `*-ops` pipelines (run now / enable or disable schedule).

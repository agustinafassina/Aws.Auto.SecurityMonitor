# 📘 Terraform Infrastructure for Scanner Jobs
This Terraform stack provisions a scalable baseline to run scanner containers recurrently on AWS.

## 🗺️ Workflow
![Terraform Infrastructure Workflow](./workflow.svg)

## 🧱 What It Creates
- One ECS Fargate cluster for scanner jobs.
- One ECR repository for all scanner images (`{project_name}/scanners`).
- One ECS task definition per scanner (same image, different `command`).
- One EventBridge schedule rule + ECS target per scanner.
- One CloudWatch log group per scanner task.
- One CloudWatch alarm per scanner rule (`FailedInvocations` metric).
- S3 bucket for findings JSON artifacts.
- IAM roles/policies for ECS task execution, scanner discovery, EventBridge, and S3 upload.

## 📈 Structure for scalability
Scalability is driven by `scanner_jobs` (map variable).  
To add a new scanner, add a folder under `scan-resources/` and an entry in `scanner_jobs` with the full `command` (e.g. `["python", "s3/scan_s3.py", "--source", "aws"]`). Terraform creates task definition, schedule, logs, and alarm — no new ECR repo.

## 🏷️ Naming convention
Resources use prefix `tf-{environment}-{project_name}` (e.g. `tf-dev-security-scan-route53`).

| Resource | Pattern |
|----------|---------|
| ECS cluster | `tf-{env}-{project}-cluster` |
| Task definition | `tf-{env}-{project}-{scanner}` |
| EventBridge rule | `tf-{env}-{project}-{scanner}-schedule` |
| ECR repository | `{project}/scanners` |
| Findings S3 bucket | `tf-{env}-{project}-findings` |

## ▶️ Usage
1. Initialize Terraform:
   ```bash
   terraform -chdir=terraform-infrastructure init
   ```

2. Copy and adjust vars:
   ```bash
   cp terraform-infrastructure/terraform.tfvars.example terraform-infrastructure/terraform.tfvars
   ```

3. First-time deploy order (avoids missing image on first apply):
   - `terraform apply` (creates ECR, cluster, task defs with per-module tags)
   - Build and push each module image (see below or use `azure-pipelines/modules/*-build.yml`)

4. Build and push per module (from repo root):
   ```bash
   docker build -f scan-resources/route53/Dockerfile -t scanners:route53 .
   docker push <account>.dkr.ecr.<region>.amazonaws.com/security-scan/scanners:route53

   docker build -f scan-resources/rds/Dockerfile -t scanners:rds .
   docker push <account>.dkr.ecr.<region>.amazonaws.com/security-scan/scanners:rds
   ```

   ECS uses `image_tag` from `scanner_jobs` (defaults to module key). After the first push, module code changes only need that module's build pipeline — no terraform apply.

ECR uses `MUTABLE` tags. A lifecycle policy expires untagged images after 7 days and keeps at most 5 images total (tune via `ecr_untagged_image_expiration_days` and `ecr_max_image_count`).

## 🔄 CI/CD (Azure DevOps)
See `azure-pipelines/README.md` for pipeline setup:
- `modules/*-build.yml` — build and push per-module ECR tag
- `modules/*-ops.yml` — manual run / enable or disable EventBridge schedule
- `infrastructure.yml` — terraform plan/apply

## ▶️ On-demand execution
Reuse the scheduled task definition without a new EventBridge rule:

```bash
export ECS_CLUSTER_NAME="tf-dev-security-scan-cluster"
export ECS_TASK_FAMILY="tf-dev-security-scan-route53"
export ECS_SUBNET_IDS="subnet-aaa,subnet-bbb"
export ECS_SECURITY_GROUP_ID="sg-xxxxxxxx"
./scripts/run-scanner.sh route53
```

Or run the module ops pipeline (`route53-ops`, `rds-ops`) with action `run-now`, `enable-schedule`, or `disable-schedule`.

## 💾 Remote State
- State is stored on S3 with native locking (`use_lockfile`, requires Terraform >= 1.10; no DynamoDB).
- Edit the placeholder bucket in `backend.tf` and create the bucket (versioning + encryption) before `terraform init`.

## 📝 Notes
- ECS tasks run with `--source aws` via the `command` in `scanner_jobs`.
- Credentials are resolved by `boto3` through the task IAM role (no API keys).
- If `vpc_id`/`subnet_ids` are not defined, Terraform uses the default VPC and its subnets.

## 🔔 Notifications
- Set `alarm_notification_emails` in `terraform.tfvars` to enable alerting (confirm each subscription via email).
- SNS topic `${name_prefix}-alarms` sends email when:
  - A scheduled or on-demand scanner task **finishes** (exit code in message; `0` = success).
  - A scanner task **fails to start** (image pull, resources, etc.).
  - EventBridge **failed invocations** alarm triggers for a schedule rule.

## 📦 Findings storage
- S3 bucket `{name_prefix}-findings` stores JSON at `findings/{scanner}/{timestamp}.json`.
- Each ECS task receives `FINDINGS_S3_BUCKET` and `FINDINGS_S3_PREFIX` via environment variables.

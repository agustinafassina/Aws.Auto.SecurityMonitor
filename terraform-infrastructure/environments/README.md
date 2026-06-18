# ☁️ Environments
Per-environment Terraform variables and remote state config. Architecture: [../README.md](../README.md).

> ⚠️ Do **not** commit `*.tfvars` or `*.backend.hcl` (only `*.example` files).

## 📋 Files

| File | Purpose |
|------|---------|
| `dev.tfvars.example` / `qa` / `prod` | `scanner_jobs`, region, emails, tags |
| `*.backend.hcl.example` | S3 state bucket, key, `use_lockfile` |

## ⚙️ Setup

```bash
cd terraform-infrastructure

cp environments/qa.tfvars.example environments/qa.tfvars
cp environments/qa.backend.hcl.example environments/qa.backend.hcl
# Edit bucket, region, alarm_notification_emails, etc.

terraform init -backend-config=environments/qa.backend.hcl
terraform plan -var-file=environments/qa.tfvars -out=tfplan
terraform apply tfplan
```

## 🗄️ State key
`s3://<bucket>/<project_name>/<environment>/terraform.tfstate`

Example: `s3://tf-security-scan-state/security-scan/qa/terraform.tfstate`

Create the state bucket once (versioning + encryption) before `terraform init`.

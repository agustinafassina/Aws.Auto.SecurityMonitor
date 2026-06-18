# 🧩 Scanner Module Template
End-to-end guide to add a scanner. Framework: [../README.md](../README.md) · Terraform/IAM: [terraform-infrastructure/README.md](../../terraform-infrastructure/README.md) · Pipelines: [azure-pipelines/README.md](../../azure-pipelines/README.md).

Replace `MODULE` with your slug (e.g. `s3`) in all steps.

## 1️⃣ Copy files

**bash:**
```bash
MODULE=s3
cp -r scan-resources/_template "scan-resources/${MODULE}"
mv "scan-resources/${MODULE}/scan_MODULE.py" "scan-resources/${MODULE}/scan_${MODULE}.py"
```

**PowerShell:**
```powershell
$module = "s3"
Copy-Item -Recurse scan-resources/_template scan-resources/$module
Rename-Item scan-resources/$module/scan_MODULE.py scan-resources/$module/scan_$module.py
```

## 2️⃣ Implement scanner
Replace `MODULE` in `scan_*.py`, `Dockerfile`, `json-example/example.json`.

Implement:
- `discover_<module>_resources()` (boto3)
- `CHECKS` map

## 3️⃣ Wire Terraform
Add to `environments/<env>.tfvars` (snippet: `terraform-scanner_jobs.hcl.example`).

Add IAM actions in `terraform-infrastructure/iam.tf`.

```bash
terraform plan -var-file=environments/<env>.tfvars -out=tfplan && terraform apply tfplan
```

## 4️⃣ Wire CI
Add module to `azure-pipelines/scanners-build.yml` matrix and `scanners-ops.yml` `scanner` values (see `azure-pipelines-build.yml.example`).

## 5️⃣ Verify and deploy
```bash
python scan-resources/s3/scan_s3.py --source file
docker build -f scan-resources/s3/Dockerfile -t scanners:s3 .
docker run --rm scanners:s3
```

Run `<module>-build` → ECR push → `<module>-ops` (`run-now` or enable schedule).

## 📁 Template files

| File | Purpose |
|------|---------|
| `scan_MODULE.py` | Scanner entrypoint |
| `Dockerfile` | Image (build context = repo root) |
| `json-example/example.json` | File-mode fixtures |
| `terraform-scanner_jobs.hcl.example` | `scanner_jobs` snippet |
| `azure-pipelines-*.example` | Pipeline stubs |

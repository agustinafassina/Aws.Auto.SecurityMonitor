# 📘 Scan Resources
Python batch scanning baseline designed to grow by module (AWS service).

## 🧱 Current Structure
```text
scan-resources/
  scanner_core.py
  requirements.txt
  run_all_scans.py
  workflow.svg
  route53/
    Dockerfile
    scan_route53.py
    json-example/example.json
  rds/
    Dockerfile
    scan_rds.py
    json-example/example.json
```

## 🗺️ Workflow
![Scan Resources Workflow](./workflow.svg)

## ▶️ Local Execution
- Route53:
  - `python scan-resources/route53/scan_route53.py --source auto`
- RDS:
  - `python scan-resources/rds/scan_rds.py --source auto`
- All modules (file mode):
  - `python scan-resources/run_all_scans.py`

### ⚙️ Script Parameters
- `--source auto|aws|file`
  - `aws`: discovers resources directly from AWS using `boto3`.
  - `file`: uses `json-example/example.json`.
  - `auto`: tries `aws` first and falls back to `file`.
- `--resources-file <path>`: optional custom local JSON path.

## 📦 Dependencies
- Python 3.12+
- Pinned in `requirements.txt` (`boto3`), used for `--source aws` and by the Docker image.
  - `pip install -r scan-resources/requirements.txt`

## 🐳 Docker (one Dockerfile per module)
Each module has its own Dockerfile under `scan-resources/<module>/`. Build context is the **repo root**:

```bash
docker build -f scan-resources/route53/Dockerfile -t scanners:route53 .
docker run --rm scanners:route53

docker build -f scan-resources/rds/Dockerfile -t scanners:rds .
docker run --rm scanners:rds
```

See `azure-pipelines/modules/*-build.yml` for CI build and ECR push per module.

## 📈 How To Add New Scanning Modules
Follow this pattern to add a new service, for example `s3`:

1. Create the module folder:
   - `scan-resources/s3/`
   - `scan-resources/s3/json-example/example.json`
2. Create the scanner script and Dockerfile:
   - `scan-resources/s3/scan_s3.py`
   - `scan-resources/s3/Dockerfile` (copy from `route53/Dockerfile`, adjust paths and CMD)
   - Reuse `scanner_core.py` (`load_resources`, `run_scan`, `ResourceScannerConfig`).
   - Implement `discover_s3_resources()` using `boto3`.
   - Support `--source auto|aws|file` and `--resources-file`.
   - Configure `FINDINGS_S3_BUCKET` and `FINDINGS_S3_PREFIX` at the top of the script.
3. (Optional) Add it to the local runner:
   - add `s3` to `run_all_scans.py`.
4. Add the module to infrastructure in `terraform.tfvars` under `scanner_jobs`:
   ```hcl
   s3 = {
     schedule_expression = "rate(7 days)"
     cpu                 = 256
     memory              = 512
     command             = ["python", "s3/scan_s3.py", "--source", "aws"]
     enabled             = true
   }
   ```
   Terraform creates ECS task, EventBridge schedule, logs, and alarm. No new ECR repo needed.
5. Add Azure DevOps pipelines:
   - `azure-pipelines/modules/s3-build.yml`
   - `azure-pipelines/modules/s3-ops.yml`
   - Copy from `route53` examples and reuse `templates/`.

## 🧾 Recommended `example.json` Format
Each resource lists the `checks` to run plus the attribute fields those checks evaluate.

```json
{
  "resources": [
    {
      "id": "resource-id",
      "type": "resource-type",
      "checks": ["check_1", "check_2"],
      "check_1": true,
      "check_2": false
    }
  ]
}
```

## 🛡️ Check Engine
- Each module registers a `CHECKS` map of `check_name -> Check(severity, fn)` (see `scan_rds.py` / `scan_route53.py`).
- `scanner_core.run_scan` evaluates each resource's `checks` and returns per-check `status` (`pass` / `fail` / `error`) and `severity`.
- Output includes a `summary` with failed resources and failed checks grouped by severity.
- Severities: `low`, `medium`, `high`, `critical`.

## 💾 Findings persistence (S3)
- Each scanner script configures `FINDINGS_S3_BUCKET` and `FINDINGS_S3_PREFIX` at the top (overridable via env).
- After each run, results are uploaded as JSON to `s3://{bucket}/{prefix}/{service}/{timestamp}.json`.
- Leave `FINDINGS_S3_BUCKET` empty locally to skip upload; ECS tasks receive bucket/prefix from Terraform env vars.
- Output includes `s3_location` with `s3_uri` on success, or `error` if upload fails.

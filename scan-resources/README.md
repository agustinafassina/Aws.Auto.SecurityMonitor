# 📘 Scan Resources
Python batch scanning baseline designed to grow by module (AWS service).

## 🧱 Current Structure
```text
scan-resources/
  scanner_core.py
  run_all_scans.py
  workflow.svg
  route53/
    scan_route53.py
    Dockerfile
    json-example/example.json
  rds/
    scan_rds.py
    Dockerfile
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
- `boto3` for `--source aws`
  - `pip install boto3`

## 🐳 Docker Execution (Batch)
Each module has its own Dockerfile to run once and exit.

- Route53
  - Build: `docker build -f scan-resources/route53/Dockerfile -t scan-route53 .`
  - Run: `docker run --rm scan-route53 --source aws`
- RDS
  - Build: `docker build -f scan-resources/rds/Dockerfile -t scan-rds .`
  - Run: `docker run --rm scan-rds --source aws`

## 📈 How To Add New Scanning Modules
Follow this pattern to add a new service, for example `s3`:

1. Create the module folder:
   - `scan-resources/s3/`
   - `scan-resources/s3/json-example/example.json`
2. Create the scanner script:
   - `scan-resources/s3/scan_s3.py`
   - Reuse `scanner_core.py` (`load_resources`, `run_scan`, `ResourceScannerConfig`).
   - Implement `discover_s3_resources()` using `boto3`.
   - Support `--source auto|aws|file` and `--resources-file`.
3. Create the module Dockerfile:
   - `scan-resources/s3/Dockerfile`
   - Follow the current Dockerfile pattern (Python slim + boto3 + script entrypoint).
4. (Optional) Add it to the local runner:
   - add `s3` to the `service_files` map in `scan-resources/run_all_scans.py`.
5. Add the module to infrastructure:
   - add an entry in `terraform-infrastructure/terraform.tfvars` under `scanner_jobs` (`s3 = { ... }`).
   - Terraform will automatically create ECR, ECS task, EventBridge rule, logs, and alarm.

## 🧾 Recommended `example.json` Format
```json
{
  "resources": [
    {
      "id": "resource-id",
      "type": "resource-type",
      "checks": ["check_1", "check_2"]
    }
  ]
}
```
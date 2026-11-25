# 📘 Scan Resources
Modular Python scanners for AWS. Every module is a self-contained package under `scan-resources/<module>/` that reuses the shared `scanner_core` check engine and ships as its own container. Add a module: [_template/README.md](_template/README.md). The `route53` module below is the reference implementation.

## 🗺️ Workflow
![Workflow](./workflow.svg)

## 🧱 Layout
```text
scan-resources/
  scanner_core.py       # shared check engine, load_resources, S3 persist
  requirements.txt      # shared deps (boto3) — every module image installs this
  requirements-dev.txt  # + pytest (tests/CI only, not shipped in images)
  tests/                # unit tests for scanner_core and each module
  _template/            # copy to add a module
  <module>/             # one folder per scanner (route53 is the first)
    Dockerfile          # build context = repo root
    scan_<module>.py    # entrypoint: discovery + CHECKS
    json-example/example.json
```

## ⚙️ Shared framework (`scanner_core.py`)
Every module builds on the same engine, so a new scanner only writes discovery + checks.

### 🛡️ Check engine
- Each module defines `CHECKS`: `check_name -> Check(severity, fn)`.
- `run_scan()` evaluates each resource's `checks` → `pass` / `fail` / `error` + severity summary.
- Reference implementation: `route53/scan_route53.py`.

### 🧾 `example.json` (file mode)
```json
{
  "resources": [
    {
      "id": "resource-id",
      "type": "resource-type",
      "checks": ["check_1"],
      "check_1": true
    }
  ]
}
```

### 📦 Findings (S3)
Modules set `FINDINGS_S3_BUCKET` and `FINDINGS_S3_PREFIX` at the top (overridden by ECS env vars). Empty bucket locally skips upload. See [terraform-infrastructure/README.md](../terraform-infrastructure/README.md) for the bucket and IAM side.

## 🌐 Reference module: route53
A worked example of the contract above.

### Local run
```bash
python scan-resources/route53/scan_route53.py --source auto
```

| Flag | Description |
|------|-------------|
| `--source auto\|aws\|file` | `aws`: boto3; `file`: `json-example/example.json`; `auto`: aws then fallback |
| `--resources-file <path>` | Custom JSON input |
| `--domain-timeout <sec>` | Per-domain AWS discovery timeout (default: 30, env: `ROUTE53_DOMAIN_TIMEOUT_SECONDS`) |
| `--max-domains <n>` | Max hosted zones per run (default: 10) |

### Batch behaviour
- Scans **one domain at a time** with logging to stderr.
- **Pushes each zone** to S3 as it completes (`…/runs/{batch_id}/zones/{zone_id}.json`) and updates a running `summary.json` (no data loss if the task dies mid-run).
- **Exit code 1** if any domain has `fail` or `error` (ECS task fails → SNS notification).
- **Timeout** → checks `fail` with `domain discovery timed out after Ns` (not `error`). API discovery errors → `error`. The scan moves on to the next domain right away; the boto3 client's own connect/read timeouts (same value) stop the abandoned call.

### Docker
Build context = repo root. CI: [azure-pipelines/scanners-build.yml](../azure-pipelines/scanners-build.yml).

```bash
docker build -f scan-resources/route53/Dockerfile -t scanners:route53 .
docker run --rm scanners:route53
```

## 🧪 Tests
Unit tests use a fake boto3 client, so they need no AWS credentials. CI runs them before each module's image build ([module-build-steps.yml](../azure-pipelines/templates/module-build-steps.yml)).

```bash
pip install -r scan-resources/requirements-dev.txt
python -m pytest scan-resources/tests -q
```

A new module adds `tests/test_<module>.py`; load it with the `load_module("<module>")` helper from `tests/conftest.py`.

## ➕ New module
Do not duplicate steps here — follow [_template/README.md](_template/README.md).

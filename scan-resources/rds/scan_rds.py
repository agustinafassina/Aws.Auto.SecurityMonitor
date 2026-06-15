from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# --- S3 findings persistence (override via env in ECS) ---
# Local: leave bucket empty to skip upload, or set e.g. "tf-dev-security-scan-findings"
FINDINGS_S3_BUCKET = os.environ.get("FINDINGS_S3_BUCKET", "")
FINDINGS_S3_PREFIX = os.environ.get("FINDINGS_S3_PREFIX", "findings/rds")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scanner_core import (
    Check,
    ResourceScannerConfig,
    load_resources,
    persist_findings_to_s3,
    run_scan,
)

DEFAULT_RESOURCES_FILE = Path(__file__).resolve().parent / "json-example" / "example.json"

MIN_BACKUP_RETENTION_DAYS = 7


def _check_storage_encrypted(resource: dict[str, Any]) -> tuple[bool, str]:
    enabled = bool(resource.get("storage_encrypted"))
    return enabled, "storage encryption enabled" if enabled else "storage is not encrypted"


def _check_backup_retention(resource: dict[str, Any]) -> tuple[bool, str]:
    days = resource.get("backup_retention_period") or 0
    ok = days >= MIN_BACKUP_RETENTION_DAYS
    return ok, f"backup retention = {days} day(s) (min {MIN_BACKUP_RETENTION_DAYS})"


def _check_deletion_protection(resource: dict[str, Any]) -> tuple[bool, str]:
    enabled = bool(resource.get("deletion_protection"))
    return enabled, "deletion protection enabled" if enabled else "deletion protection disabled"


def _check_iam_authentication(resource: dict[str, Any]) -> tuple[bool, str]:
    enabled = bool(resource.get("iam_authentication"))
    return enabled, "IAM authentication enabled" if enabled else "IAM authentication disabled"


CHECKS: dict[str, Check] = {
    "storage_encrypted": Check("high", _check_storage_encrypted),
    "backup_retention_period": Check("medium", _check_backup_retention),
    "deletion_protection": Check("medium", _check_deletion_protection),
    "iam_authentication": Check("medium", _check_iam_authentication),
}


def discover_rds_resources() -> list[dict[str, Any]]:
    import boto3

    client = boto3.client("rds")
    resources: list[dict[str, Any]] = []

    db_instances_paginator = client.get_paginator("describe_db_instances")
    for page in db_instances_paginator.paginate():
        for instance in page.get("DBInstances", []):
            resources.append(
                {
                    "id": instance.get("DBInstanceIdentifier", "unknown-instance"),
                    "type": "db_instance",
                    "checks": ["storage_encrypted", "backup_retention_period"],
                    "engine": instance.get("Engine"),
                    "multi_az": instance.get("MultiAZ"),
                    "storage_encrypted": instance.get("StorageEncrypted", False),
                    "backup_retention_period": instance.get("BackupRetentionPeriod", 0),
                }
            )

    db_clusters_paginator = client.get_paginator("describe_db_clusters")
    for page in db_clusters_paginator.paginate():
        for cluster in page.get("DBClusters", []):
            resources.append(
                {
                    "id": cluster.get("DBClusterIdentifier", "unknown-cluster"),
                    "type": "db_cluster",
                    "checks": ["deletion_protection", "iam_authentication"],
                    "engine": cluster.get("Engine"),
                    "deletion_protection": cluster.get("DeletionProtection", False),
                    "iam_authentication": cluster.get("IAMDatabaseAuthenticationEnabled", False),
                }
            )

    return resources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan RDS resources from file or AWS.")
    parser.add_argument(
        "--resources-file",
        default=str(DEFAULT_RESOURCES_FILE),
        help="Path to a JSON file with resources to scan.",
    )
    parser.add_argument(
        "--source",
        choices=["auto", "file", "aws"],
        default="auto",
        help="Source for resources: file, aws, or auto (try aws then fallback file).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    resources_file = Path(args.resources_file)
    source_used = args.source
    aws_error: str | None = None

    if args.source == "file":
        resources = load_resources(resources_file)
        source_used = "file"
    elif args.source == "aws":
        resources = discover_rds_resources()
        source_used = "aws"
    else:
        try:
            resources = discover_rds_resources()
            source_used = "aws"
        except Exception as exc:  # noqa: BLE001
            resources = load_resources(resources_file)
            source_used = "file"
            aws_error = str(exc)

    config = ResourceScannerConfig(
        service_name="rds",
        resources=resources,
        source=source_used,
    )
    result = run_scan(config, CHECKS)
    if aws_error:
        result["aws_discovery_error"] = aws_error

    s3_location = persist_findings_to_s3(result, FINDINGS_S3_BUCKET, FINDINGS_S3_PREFIX)
    if s3_location:
        result["s3_location"] = s3_location

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

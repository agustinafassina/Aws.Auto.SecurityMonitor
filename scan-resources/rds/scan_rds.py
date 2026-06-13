from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scanner_core import ResourceScannerConfig, load_resources, run_scan

DEFAULT_RESOURCES_FILE = Path(__file__).resolve().parent / "json-example" / "example.json"


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
                    "iam_authentication": cluster.get("IAMDatabaseAuthenticationEnabled"),
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
    result = run_scan(config)
    if aws_error:
        result["aws_discovery_error"] = aws_error
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
FINDINGS_S3_PREFIX = os.environ.get("FINDINGS_S3_PREFIX", "findings/route53")

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
MAX_DOMAINS = 10


def _check_dnssec_enabled(resource: dict[str, Any]) -> tuple[bool, str]:
    enabled = bool(resource.get("dnssec_enabled"))
    return enabled, "DNSSEC signing active" if enabled else "DNSSEC not enabled"


def _check_query_logging_enabled(resource: dict[str, Any]) -> tuple[bool, str]:
    enabled = bool(resource.get("query_logging_enabled"))
    return enabled, "query logging configured" if enabled else "query logging not configured"


CHECKS: dict[str, Check] = {
    "dnssec_enabled": Check("medium", _check_dnssec_enabled),
    "query_logging_enabled": Check("low", _check_query_logging_enabled),
}


def _zone_dnssec_enabled(client: Any, zone_id: str) -> bool:
    try:
        response = client.get_dnssec(HostedZoneId=zone_id)
    except Exception:  # noqa: BLE001
        return False
    key_signing_keys = response.get("KeySigningKeys", [])
    return any(ksk.get("Status") == "ACTIVE" for ksk in key_signing_keys)


def _zone_query_logging_enabled(client: Any, zone_id: str) -> bool:
    try:
        response = client.list_query_logging_configs(HostedZoneId=zone_id)
    except Exception:  # noqa: BLE001
        return False
    return len(response.get("QueryLoggingConfigs", [])) > 0


def discover_route53_resources() -> list[dict[str, Any]]:
    import boto3

    client = boto3.client("route53")
    paginator = client.get_paginator("list_hosted_zones")

    resources: list[dict[str, Any]] = []
    for page in paginator.paginate():
        for hosted_zone in page.get("HostedZones", []):
            zone_id_raw = hosted_zone.get("Id", "")
            zone_id = zone_id_raw.split("/")[-1] if zone_id_raw else hosted_zone.get("Name", "unknown")
            is_private = hosted_zone.get("Config", {}).get("PrivateZone", False)
            resources.append(
                {
                    "id": zone_id,
                    "name": hosted_zone.get("Name"),
                    "type": "hosted_zone",
                    "checks": ["dnssec_enabled", "query_logging_enabled"],
                    "private_zone": is_private,
                    "dnssec_enabled": _zone_dnssec_enabled(client, zone_id),
                    "query_logging_enabled": _zone_query_logging_enabled(client, zone_id),
                }
            )
            if len(resources) >= MAX_DOMAINS:
                return resources

    return resources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan Route53 resources from file or AWS.")
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
        resources = discover_route53_resources()
        source_used = "aws"
    else:
        try:
            resources = discover_route53_resources()
            source_used = "aws"
        except Exception as exc:  # noqa: BLE001
            resources = load_resources(resources_file)
            source_used = "file"
            aws_error = str(exc)

    if len(resources) > MAX_DOMAINS:
        resources = resources[:MAX_DOMAINS]

    config = ResourceScannerConfig(
        service_name="route53",
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

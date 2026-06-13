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


def discover_route53_resources() -> list[dict[str, Any]]:
    import boto3

    client = boto3.client("route53")
    paginator = client.get_paginator("list_hosted_zones")

    resources: list[dict[str, Any]] = []
    for page in paginator.paginate():
        for hosted_zone in page.get("HostedZones", []):
            zone_id_raw = hosted_zone.get("Id", "")
            zone_id = zone_id_raw.split("/")[-1] if zone_id_raw else hosted_zone.get("Name", "unknown")
            resources.append(
                {
                    "id": zone_id,
                    "name": hosted_zone.get("Name"),
                    "type": "hosted_zone",
                    "checks": ["dnssec_enabled", "query_logging_enabled"],
                    "private_zone": hosted_zone.get("Config", {}).get("PrivateZone", False),
                }
            )

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

    config = ResourceScannerConfig(
        service_name="route53",
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

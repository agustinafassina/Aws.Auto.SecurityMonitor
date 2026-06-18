from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# --- S3 findings persistence (override via env in ECS) ---
FINDINGS_S3_BUCKET = os.environ.get("FINDINGS_S3_BUCKET", "")
FINDINGS_S3_PREFIX = os.environ.get("FINDINGS_S3_PREFIX", "findings/MODULE")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scanner_core import (
    Check,
    ResourceScannerConfig,
    is_batch_failed,
    load_resources,
    persist_findings_to_s3,
    run_scan,
)

DEFAULT_RESOURCES_FILE = Path(__file__).resolve().parent / "json-example" / "example.json"

# Optional: cap resources discovered from AWS (remove or adjust per module).
MAX_RESOURCES = 100


def _check_example_secure(resource: dict[str, Any]) -> tuple[bool, str]:
    """Replace with real checks. Reads attributes set during discovery or in example.json."""
    secure = bool(resource.get("is_secure"))
    return secure, "resource meets baseline" if secure else "resource does not meet baseline"


CHECKS: dict[str, Check] = {
    "example_secure": Check("medium", _check_example_secure),
}


def discover_MODULE_resources() -> list[dict[str, Any]]:
    """Discover resources from AWS. Replace MODULE, boto3 client, and pagination logic."""
    import boto3

    client = boto3.client("MODULE")  # TODO: e.g. boto3.client("s3")
    _ = client

    # TODO: implement discovery; each resource must include "checks" and fields your CHECKS need.
    return []


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan MODULE resources from file or AWS.")
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
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="CI smoke: exit 0 if the scan completes (findings may still fail).",
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
        resources = discover_MODULE_resources()
        source_used = "aws"
    else:
        try:
            resources = discover_MODULE_resources()
            source_used = "aws"
        except Exception as exc:  # noqa: BLE001
            resources = load_resources(resources_file)
            source_used = "file"
            aws_error = str(exc)

    if len(resources) > MAX_RESOURCES:
        resources = resources[:MAX_RESOURCES]

    config = ResourceScannerConfig(
        service_name="MODULE",
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

    if args.smoke_test:
        return 0
    return 1 if is_batch_failed(result["results"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())

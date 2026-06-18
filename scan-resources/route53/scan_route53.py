from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- S3 findings persistence (override via env in ECS) ---
FINDINGS_S3_BUCKET = os.environ.get("FINDINGS_S3_BUCKET", "")
FINDINGS_S3_PREFIX = os.environ.get("FINDINGS_S3_PREFIX", "findings/route53")
DOMAIN_TIMEOUT_SECONDS = int(os.environ.get("ROUTE53_DOMAIN_TIMEOUT_SECONDS", "30"))

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from scanner_core import (
    Check,
    build_scan_payload,
    is_batch_failed,
    load_resources,
    persist_findings_to_s3,
    persist_json_to_s3,
    scan_resource,
)

DEFAULT_RESOURCES_FILE = Path(__file__).resolve().parent / "json-example" / "example.json"
MAX_DOMAINS = 10
SERVICE_NAME = "route53"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [route53] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def _discovery_fail_detail(resource: dict[str, Any]) -> str | None:
    if resource.get("discovery_timeout"):
        seconds = resource.get("discovery_timeout_seconds", DOMAIN_TIMEOUT_SECONDS)
        return f"domain discovery timed out after {seconds}s"
    if resource.get("discovery_error"):
        return f"discovery failed: {resource['discovery_error']}"
    return None


def _check_dnssec_enabled(resource: dict[str, Any]) -> tuple[bool, str]:
    detail = _discovery_fail_detail(resource)
    if detail:
        return False, detail
    enabled = bool(resource.get("dnssec_enabled"))
    return enabled, "DNSSEC signing active" if enabled else "DNSSEC not enabled"


def _check_query_logging_enabled(resource: dict[str, Any]) -> tuple[bool, str]:
    detail = _discovery_fail_detail(resource)
    if detail:
        return False, detail
    enabled = bool(resource.get("query_logging_enabled"))
    return enabled, "query logging configured" if enabled else "query logging not configured"


CHECKS: dict[str, Check] = {
    "dnssec_enabled": Check("medium", _check_dnssec_enabled),
    "query_logging_enabled": Check("low", _check_query_logging_enabled),
}


def _zone_dnssec_enabled(client: Any, zone_id: str) -> bool:
    response = client.get_dnssec(HostedZoneId=zone_id)
    key_signing_keys = response.get("KeySigningKeys", [])
    return any(ksk.get("Status") == "ACTIVE" for ksk in key_signing_keys)


def _zone_query_logging_enabled(client: Any, zone_id: str) -> bool:
    response = client.list_query_logging_configs(HostedZoneId=zone_id)
    return len(response.get("QueryLoggingConfigs", [])) > 0


def _enrich_zone(client: Any, zone_id: str, zone_name: str, is_private: bool) -> dict[str, Any]:
    dnssec_enabled = _zone_dnssec_enabled(client, zone_id)
    query_logging_enabled = _zone_query_logging_enabled(client, zone_id)
    return {
        "id": zone_id,
        "name": zone_name,
        "type": "hosted_zone",
        "checks": ["dnssec_enabled", "query_logging_enabled"],
        "private_zone": is_private,
        "dnssec_enabled": dnssec_enabled,
        "query_logging_enabled": query_logging_enabled,
    }


def _enrich_zone_with_timeout(
    client: Any,
    zone_id: str,
    zone_name: str,
    is_private: bool,
    timeout_seconds: int,
) -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_enrich_zone, client, zone_id, zone_name, is_private)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError:
            logger.warning("Domain %s (%s) timed out after %ss", zone_name, zone_id, timeout_seconds)
            return {
                "id": zone_id,
                "name": zone_name,
                "type": "hosted_zone",
                "checks": ["dnssec_enabled", "query_logging_enabled"],
                "private_zone": is_private,
                "discovery_timeout": True,
                "discovery_timeout_seconds": timeout_seconds,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("Domain %s (%s) discovery failed: %s", zone_name, zone_id, exc)
            return {
                "id": zone_id,
                "name": zone_name,
                "type": "hosted_zone",
                "checks": ["dnssec_enabled", "query_logging_enabled"],
                "private_zone": is_private,
                "dnssec_enabled": False,
                "query_logging_enabled": False,
                "discovery_error": str(exc),
            }


def _list_hosted_zone_stubs(client: Any, max_domains: int) -> list[dict[str, Any]]:
    paginator = client.get_paginator("list_hosted_zones")
    stubs: list[dict[str, Any]] = []
    for page in paginator.paginate():
        for hosted_zone in page.get("HostedZones", []):
            zone_id_raw = hosted_zone.get("Id", "")
            zone_id = zone_id_raw.split("/")[-1] if zone_id_raw else hosted_zone.get("Name", "unknown")
            stubs.append(
                {
                    "id": zone_id,
                    "name": hosted_zone.get("Name"),
                    "private_zone": hosted_zone.get("Config", {}).get("PrivateZone", False),
                }
            )
            if len(stubs) >= max_domains:
                return stubs
    return stubs


def _s3_key_for_zone(prefix: str, batch_id: str, zone_id: str) -> str:
    safe_zone_id = zone_id.replace("/", "_")
    normalized = prefix.strip("/")
    return f"{normalized}/runs/{batch_id}/zones/{safe_zone_id}.json"


def _s3_key_for_summary(prefix: str, batch_id: str) -> str:
    normalized = prefix.strip("/")
    return f"{normalized}/runs/{batch_id}/summary.json"


def _persist_zone_result(
    bucket: str,
    prefix: str,
    batch_id: str,
    zone_id: str,
    zone_payload: dict[str, Any],
) -> dict[str, Any] | None:
    if not bucket:
        return None
    key = _s3_key_for_zone(prefix, batch_id, zone_id)
    location = persist_json_to_s3(zone_payload, bucket, key)
    if location.get("error"):
        logger.error("S3 upload failed for zone %s: %s", zone_id, location["error"])
    else:
        logger.info("Pushed zone result to %s", location.get("s3_uri"))
    return location


def _persist_running_summary(
    bucket: str,
    prefix: str,
    batch_id: str,
    source: str,
    scan_results: list[dict[str, Any]],
    *,
    partial: bool,
) -> dict[str, Any] | None:
    if not bucket:
        return None
    payload = build_scan_payload(
        SERVICE_NAME,
        source,
        scan_results,
        batch_id=batch_id,
        extra={"partial": partial},
    )
    key = _s3_key_for_summary(prefix, batch_id)
    location = persist_json_to_s3(payload, bucket, key)
    if location.get("error"):
        logger.error("S3 summary upload failed: %s", location["error"])
    else:
        logger.info("Pushed %s summary to %s", "partial" if partial else "final", location.get("s3_uri"))
    return location


def _scan_resource_record(resource: dict[str, Any]) -> dict[str, Any]:
    result = scan_resource(service_name=SERVICE_NAME, resource=resource, checks=CHECKS)
    if resource.get("discovery_timeout"):
        result["discovery_timeout"] = True
        result["discovery_timeout_seconds"] = resource.get("discovery_timeout_seconds")
    elif resource.get("discovery_error"):
        result["status"] = "error"
        result["discovery_error"] = resource["discovery_error"]
    return result


def run_batch_scan(
    resources: list[dict[str, Any]],
    source: str,
    *,
    domain_timeout: int,
    enrich_from_aws: bool,
) -> tuple[dict[str, Any], int]:
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    scan_results: list[dict[str, Any]] = []
    zone_s3_locations: list[dict[str, Any]] = []

    logger.info(
        "Starting batch %s: %s domain(s), source=%s, timeout=%ss",
        batch_id,
        len(resources),
        source,
        domain_timeout,
    )

    client = None
    if enrich_from_aws:
        import boto3

        client = boto3.client("route53")
        stubs = _list_hosted_zone_stubs(client, MAX_DOMAINS)
        resources = stubs
        logger.info("Listed %s hosted zone(s) from AWS", len(resources))

    for index, item in enumerate(resources, start=1):
        if enrich_from_aws and client is not None:
            zone_id = str(item["id"])
            zone_name = str(item.get("name", zone_id))
            logger.info("[%s/%s] Scanning domain %s (%s)", index, len(resources), zone_name, zone_id)
            resource = _enrich_zone_with_timeout(
                client,
                zone_id,
                zone_name,
                bool(item.get("private_zone", False)),
                domain_timeout,
            )
        else:
            zone_id = str(item.get("id") or item.get("name") or f"zone-{index}")
            zone_name = str(item.get("name", zone_id))
            logger.info("[%s/%s] Scanning domain %s (%s)", index, len(resources), zone_name, zone_id)
            resource = dict(item)

        scan_result = _scan_resource_record(resource)
        scan_results.append(scan_result)

        zone_payload = {
            "batch_id": batch_id,
            "service": SERVICE_NAME,
            "source": source,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "resource": resource,
            "result": scan_result,
        }
        location = _persist_zone_result(
            FINDINGS_S3_BUCKET,
            FINDINGS_S3_PREFIX,
            batch_id,
            zone_id,
            zone_payload,
        )
        if location:
            zone_s3_locations.append(location)

        _persist_running_summary(
            FINDINGS_S3_BUCKET,
            FINDINGS_S3_PREFIX,
            batch_id,
            source,
            scan_results,
            partial=True,
        )

        logger.info(
            "[%s/%s] Domain %s finished: status=%s",
            index,
            len(resources),
            zone_name,
            scan_result["status"],
        )

    final = build_scan_payload(SERVICE_NAME, source, scan_results, batch_id=batch_id)
    summary_location = _persist_running_summary(
        FINDINGS_S3_BUCKET,
        FINDINGS_S3_PREFIX,
        batch_id,
        source,
        scan_results,
        partial=False,
    )
    if summary_location:
        final["s3_location"] = summary_location
    if zone_s3_locations:
        final["zone_s3_locations"] = zone_s3_locations

    # Legacy final artifact (single file per run timestamp)
    legacy_location = persist_findings_to_s3(final, FINDINGS_S3_BUCKET, FINDINGS_S3_PREFIX)
    if legacy_location and "s3_location" not in final:
        final["s3_location"] = legacy_location

    exit_code = 1 if is_batch_failed(scan_results) else 0
    if exit_code != 0:
        logger.error(
            "Batch %s failed: %s resource(s) with fail/error",
            batch_id,
            final["summary"]["resources_failed"],
        )
    else:
        logger.info("Batch %s completed successfully", batch_id)

    return final, exit_code


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
    parser.add_argument(
        "--domain-timeout",
        type=int,
        default=DOMAIN_TIMEOUT_SECONDS,
        help="Seconds to wait per domain for AWS discovery (DNSSEC, query logging).",
    )
    parser.add_argument(
        "--max-domains",
        type=int,
        default=MAX_DOMAINS,
        help="Maximum number of hosted zones to scan.",
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
    enrich_from_aws = False
    resources: list[dict[str, Any]] = []

    global MAX_DOMAINS  # noqa: PLW0603
    MAX_DOMAINS = max(1, args.max_domains)

    if args.source == "file":
        resources = load_resources(resources_file)[:MAX_DOMAINS]
        source_used = "file"
    elif args.source == "aws":
        enrich_from_aws = True
        source_used = "aws"
    else:
        try:
            import boto3

            boto3.client("route53").list_hosted_zones(MaxItems="1")
            enrich_from_aws = True
            source_used = "aws"
        except Exception as exc:  # noqa: BLE001
            resources = load_resources(resources_file)[:MAX_DOMAINS]
            source_used = "file"
            aws_error = str(exc)
            enrich_from_aws = False

    if not enrich_from_aws and not resources:
        resources = load_resources(resources_file)[:MAX_DOMAINS]

    try:
        result, exit_code = run_batch_scan(
            resources,
            source_used,
            domain_timeout=args.domain_timeout,
            enrich_from_aws=enrich_from_aws,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Batch scan aborted: %s", exc)
        print(json.dumps({"service": SERVICE_NAME, "error": str(exc)}, indent=2))
        return 1

    if aws_error:
        result["aws_discovery_error"] = aws_error

    print(json.dumps(result, indent=2))
    if args.smoke_test:
        logger.info("Smoke test mode: exiting 0 (batch_status=%s)", result.get("summary", {}).get("batch_status"))
        return 0
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

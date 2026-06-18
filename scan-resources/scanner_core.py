from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

CheckFn = Callable[[dict[str, Any]], tuple[bool, str]]

SEVERITIES = ("low", "medium", "high", "critical")


@dataclass
class Check:
    severity: str
    evaluate: CheckFn


@dataclass
class ResourceScannerConfig:
    service_name: str
    resources_file: Path | None = None
    resources: list[dict[str, Any]] | None = None
    source: str = "file"


def _normalize_resources(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        resources = payload.get("resources", [])
        if isinstance(resources, list):
            return [item for item in resources if isinstance(item, dict)]

    return []


def load_resources(resources_file: Path) -> list[dict[str, Any]]:
    raw_content = resources_file.read_text(encoding="utf-8").strip()
    if not raw_content:
        return []

    payload = json.loads(raw_content)
    return _normalize_resources(payload)


def _evaluate_check(name: str, check: Check, resource: dict[str, Any]) -> dict[str, Any]:
    try:
        passed, detail = check.evaluate(resource)
    except Exception as exc:  # noqa: BLE001
        return {
            "check": name,
            "status": "error",
            "severity": check.severity,
            "detail": f"evaluation error: {exc}",
        }

    return {
        "check": name,
        "status": "pass" if passed else "fail",
        "severity": check.severity,
        "detail": detail,
    }


def scan_resource(
    service_name: str,
    resource: dict[str, Any],
    checks: dict[str, Check],
) -> dict[str, Any]:
    requested = resource.get("checks", [])
    requested = requested if isinstance(requested, list) else []

    check_results: list[dict[str, Any]] = []
    for name in requested:
        check = checks.get(name)
        if check is None:
            check_results.append(
                {
                    "check": name,
                    "status": "error",
                    "severity": "unknown",
                    "detail": "no check implementation registered",
                }
            )
            continue
        check_results.append(_evaluate_check(name, check, resource))

    has_fail = any(result["status"] == "fail" for result in check_results)
    has_error = any(result["status"] == "error" for result in check_results)

    if has_fail:
        status = "fail"
    elif has_error:
        status = "error"
    else:
        status = "pass"

    return {
        "resource_id": resource.get("id") or resource.get("name") or "unknown",
        "resource_type": resource.get("type", "unknown"),
        "status": status,
        "checks": check_results,
    }


def _build_summary(scan_results: list[dict[str, Any]]) -> dict[str, Any]:
    by_severity = {severity: 0 for severity in SEVERITIES}
    failed_checks = 0

    for resource in scan_results:
        for check in resource["checks"]:
            if check["status"] == "fail":
                failed_checks += 1
                if check["severity"] in by_severity:
                    by_severity[check["severity"]] += 1

    resources_failed = sum(1 for r in scan_results if r["status"] in ("fail", "error"))

    return {
        "resources_total": len(scan_results),
        "resources_failed": resources_failed,
        "resources_errored": sum(1 for r in scan_results if r["status"] == "error"),
        "checks_failed": failed_checks,
        "failed_by_severity": by_severity,
        "batch_status": "fail" if resources_failed > 0 else "pass",
    }


def build_scan_payload(
    service_name: str,
    source: str,
    scan_results: list[dict[str, Any]],
    *,
    batch_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "service": service_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "resource_count": len(scan_results),
        "summary": _build_summary(scan_results),
        "results": scan_results,
    }
    if batch_id:
        payload["batch_id"] = batch_id
    if extra:
        payload.update(extra)
    return payload


def is_batch_failed(scan_results: list[dict[str, Any]]) -> bool:
    return any(result["status"] in ("fail", "error") for result in scan_results)


def run_scan(
    config: ResourceScannerConfig,
    checks: dict[str, Check] | None = None,
) -> dict[str, Any]:
    checks = checks or {}

    if config.resources is not None:
        resources = config.resources
    elif config.resources_file is not None:
        resources = load_resources(config.resources_file)
    else:
        resources = []

    scan_results = [
        scan_resource(service_name=config.service_name, resource=resource, checks=checks)
        for resource in resources
    ]

    return {
        "service": config.service_name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": config.source,
        "resource_count": len(resources),
        "summary": _build_summary(scan_results),
        "results": scan_results,
    }


def _build_s3_key(prefix: str, service_name: str, timestamp_utc: str) -> str:
    safe_timestamp = timestamp_utc.replace(":", "-")
    normalized_prefix = prefix.strip("/")
    if normalized_prefix:
        return f"{normalized_prefix}/{service_name}/{safe_timestamp}.json"
    return f"{service_name}/{safe_timestamp}.json"


def persist_json_to_s3(payload: dict[str, Any], bucket: str, key: str) -> dict[str, Any]:
    if not bucket:
        return {"skipped": True, "reason": "empty bucket"}

    try:
        import boto3

        body = json.dumps(payload, indent=2).encode("utf-8")
        client = boto3.client("s3")
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        return {"bucket": bucket, "key": key, "s3_uri": f"s3://{bucket}/{key}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "key": key}


def persist_findings_to_s3(
    result: dict[str, Any],
    bucket: str,
    prefix: str,
) -> dict[str, Any] | None:
    if not bucket:
        return None

    try:
        import boto3

        key = _build_s3_key(prefix, result["service"], result["timestamp_utc"])
        body = json.dumps(result, indent=2).encode("utf-8")

        client = boto3.client("s3")
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )

        return {"bucket": bucket, "key": key, "s3_uri": f"s3://{bucket}/{key}"}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}

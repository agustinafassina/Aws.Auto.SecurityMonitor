from __future__ import annotations

import json

from scanner_core import (
    Check,
    build_scan_payload,
    is_batch_failed,
    load_resources,
    persist_json_to_s3,
    scan_resource,
)


def _passes(_resource):
    return True, "ok"


def _fails(_resource):
    return False, "bad"


def _raises(_resource):
    raise ValueError("boom")


CHECKS = {
    "passes": Check("low", _passes),
    "fails": Check("high", _fails),
    "raises": Check("medium", _raises),
}


# --- load_resources -------------------------------------------------------

def test_load_resources_accepts_wrapped_list(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"resources": [{"id": "a"}, "junk", {"id": "b"}]}), encoding="utf-8")
    assert load_resources(f) == [{"id": "a"}, {"id": "b"}]


def test_load_resources_accepts_bare_list(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps([{"id": "a"}, 3]), encoding="utf-8")
    assert load_resources(f) == [{"id": "a"}]


def test_load_resources_empty_file(tmp_path):
    f = tmp_path / "r.json"
    f.write_text("   \n", encoding="utf-8")
    assert load_resources(f) == []


def test_load_resources_unexpected_shape(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"resources": "nope"}), encoding="utf-8")
    assert load_resources(f) == []


# --- scan_resource --------------------------------------------------------

def test_scan_resource_all_pass():
    result = scan_resource("svc", {"id": "r1", "type": "t", "checks": ["passes"]}, CHECKS)
    assert result["status"] == "pass"
    assert result["resource_id"] == "r1"
    assert result["resource_type"] == "t"
    assert result["checks"] == [
        {"check": "passes", "status": "pass", "severity": "low", "detail": "ok"}
    ]


def test_scan_resource_fail_wins_over_error():
    result = scan_resource("svc", {"id": "r1", "checks": ["raises", "fails"]}, CHECKS)
    assert result["status"] == "fail"


def test_scan_resource_check_exception_is_error():
    result = scan_resource("svc", {"id": "r1", "checks": ["raises"]}, CHECKS)
    assert result["status"] == "error"
    assert result["checks"][0]["status"] == "error"
    assert "boom" in result["checks"][0]["detail"]


def test_scan_resource_unknown_check_is_error():
    result = scan_resource("svc", {"id": "r1", "checks": ["missing"]}, CHECKS)
    assert result["status"] == "error"
    assert result["checks"][0]["severity"] == "unknown"


def test_scan_resource_id_falls_back_to_name_then_unknown():
    assert scan_resource("svc", {"name": "n"}, CHECKS)["resource_id"] == "n"
    assert scan_resource("svc", {}, CHECKS)["resource_id"] == "unknown"


def test_scan_resource_non_list_checks_means_no_checks():
    result = scan_resource("svc", {"id": "r1", "checks": "passes"}, CHECKS)
    assert result["checks"] == []
    assert result["status"] == "pass"


# --- summary / payload ----------------------------------------------------

def test_build_scan_payload_summary_counts():
    results = [
        scan_resource("svc", {"id": "a", "checks": ["passes"]}, CHECKS),
        scan_resource("svc", {"id": "b", "checks": ["fails", "passes"]}, CHECKS),
        scan_resource("svc", {"id": "c", "checks": ["raises"]}, CHECKS),
    ]
    payload = build_scan_payload("svc", "file", results, batch_id="B1", extra={"partial": True})

    assert payload["service"] == "svc"
    assert payload["batch_id"] == "B1"
    assert payload["partial"] is True
    assert payload["resource_count"] == 3

    summary = payload["summary"]
    assert summary["resources_total"] == 3
    assert summary["resources_failed"] == 2
    assert summary["resources_errored"] == 1
    assert summary["checks_failed"] == 1
    assert summary["failed_by_severity"] == {"low": 0, "medium": 0, "high": 1, "critical": 0}
    assert summary["batch_status"] == "fail"


def test_build_scan_payload_all_pass():
    results = [scan_resource("svc", {"id": "a", "checks": ["passes"]}, CHECKS)]
    payload = build_scan_payload("svc", "file", results)
    assert payload["summary"]["batch_status"] == "pass"
    assert "batch_id" not in payload


def test_is_batch_failed():
    assert is_batch_failed([{"status": "pass"}]) is False
    assert is_batch_failed([{"status": "pass"}, {"status": "error"}]) is True
    assert is_batch_failed([]) is False


# --- S3 -------------------------------------------------------------------

def test_persist_json_to_s3_skips_without_bucket():
    assert persist_json_to_s3({"a": 1}, "", "k") == {"skipped": True, "reason": "empty bucket"}

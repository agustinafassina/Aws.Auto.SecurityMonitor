from __future__ import annotations

import threading
import time

import pytest


class FakeRoute53Client:
    """Minimal stand-in for the boto3 Route53 client."""

    def __init__(self, zones=None, dnssec=None, logging=None, hang=None, raise_on=None):
        self.zones = zones or []
        self.dnssec = dnssec or {}
        self.logging = logging or {}
        self.hang = hang  # threading.Event: get_dnssec blocks until it is set
        self.raise_on = raise_on or set()

    def get_paginator(self, name):
        assert name == "list_hosted_zones"
        zones = self.zones

        class _Paginator:
            def paginate(self):
                # two pages to exercise pagination
                yield {"HostedZones": zones[:2]}
                yield {"HostedZones": zones[2:]}

        return _Paginator()

    def get_dnssec(self, HostedZoneId):
        if self.hang is not None:
            self.hang.wait(timeout=10)
        if HostedZoneId in self.raise_on:
            raise RuntimeError("AccessDenied")
        status = "ACTIVE" if self.dnssec.get(HostedZoneId) else "INACTIVE"
        return {"KeySigningKeys": [{"Status": status}]}

    def list_query_logging_configs(self, HostedZoneId):
        configs = [{"Id": "cfg"}] if self.logging.get(HostedZoneId) else []
        return {"QueryLoggingConfigs": configs}


def _zone(zone_id, name, private=False):
    return {"Id": f"/hostedzone/{zone_id}", "Name": name, "Config": {"PrivateZone": private}}


@pytest.fixture(autouse=True)
def _no_s3(route53, monkeypatch):
    monkeypatch.setattr(route53, "FINDINGS_S3_BUCKET", "")


# --- checks ---------------------------------------------------------------

def test_dnssec_check(route53):
    assert route53._check_dnssec_enabled({"dnssec_enabled": True}) == (True, "DNSSEC signing active")
    assert route53._check_dnssec_enabled({"dnssec_enabled": False}) == (False, "DNSSEC not enabled")


def test_query_logging_check(route53):
    assert route53._check_query_logging_enabled({"query_logging_enabled": True})[0] is True
    assert route53._check_query_logging_enabled({})[0] is False


def test_checks_fail_on_discovery_timeout_and_error(route53):
    timed_out = {"discovery_timeout": True, "discovery_timeout_seconds": 5, "dnssec_enabled": True}
    passed, detail = route53._check_dnssec_enabled(timed_out)
    assert passed is False
    assert "timed out after 5s" in detail

    errored = {"discovery_error": "AccessDenied", "query_logging_enabled": True}
    passed, detail = route53._check_query_logging_enabled(errored)
    assert passed is False
    assert "AccessDenied" in detail


# --- discovery ------------------------------------------------------------

def test_list_hosted_zone_stubs_strips_prefix_and_respects_limit(route53):
    client = FakeRoute53Client(
        zones=[_zone("Z1", "a.com."), _zone("Z2", "b.com.", private=True), _zone("Z3", "c.com.")]
    )
    stubs = route53._list_hosted_zone_stubs(client, max_domains=2)
    assert stubs == [
        {"id": "Z1", "name": "a.com.", "private_zone": False},
        {"id": "Z2", "name": "b.com.", "private_zone": True},
    ]
    assert len(route53._list_hosted_zone_stubs(client, max_domains=10)) == 3


def test_enrich_zone_reads_dnssec_and_logging(route53):
    client = FakeRoute53Client(dnssec={"Z1": True}, logging={"Z1": False})
    resource = route53._enrich_zone_with_timeout(client, "Z1", "a.com.", False, timeout_seconds=5)
    assert resource["dnssec_enabled"] is True
    assert resource["query_logging_enabled"] is False
    assert "discovery_timeout" not in resource


def test_enrich_zone_records_discovery_error(route53):
    client = FakeRoute53Client(raise_on={"Z1"})
    resource = route53._enrich_zone_with_timeout(client, "Z1", "a.com.", False, timeout_seconds=5)
    assert resource["discovery_error"] == "AccessDenied"


def test_enrich_zone_timeout_returns_promptly(route53):
    """Regression: the timeout must not wait for the hung AWS call to finish."""
    release = threading.Event()
    client = FakeRoute53Client(hang=release)
    try:
        started = time.monotonic()
        resource = route53._enrich_zone_with_timeout(client, "Z1", "a.com.", False, timeout_seconds=0.2)
        elapsed = time.monotonic() - started
    finally:
        release.set()  # let the abandoned worker finish

    assert resource["discovery_timeout"] is True
    assert elapsed < 2, f"timeout blocked for {elapsed:.1f}s"


# --- batch ----------------------------------------------------------------

def test_run_batch_scan_from_file_resources(route53):
    resources = [
        {"id": "ok", "type": "hosted_zone", "checks": ["dnssec_enabled"], "dnssec_enabled": True},
    ]
    result, exit_code = route53.run_batch_scan(resources, "file", domain_timeout=5, enrich_from_aws=False)
    assert exit_code == 0
    assert result["summary"]["batch_status"] == "pass"
    assert result["source"] == "file"


def test_run_batch_scan_fails_when_any_check_fails(route53):
    resources = [
        {"id": "ok", "checks": ["dnssec_enabled"], "dnssec_enabled": True},
        {"id": "bad", "checks": ["query_logging_enabled"], "query_logging_enabled": False},
    ]
    result, exit_code = route53.run_batch_scan(resources, "file", domain_timeout=5, enrich_from_aws=False)
    assert exit_code == 1
    assert result["summary"]["resources_failed"] == 1


def test_run_batch_scan_from_aws(route53, monkeypatch):
    client = FakeRoute53Client(
        zones=[_zone("Z1", "a.com."), _zone("Z2", "b.com.")],
        dnssec={"Z1": True, "Z2": True},
        logging={"Z1": True},
        raise_on={"Z2"},
    )
    monkeypatch.setattr(route53, "_route53_client", lambda _timeout: client)

    result, exit_code = route53.run_batch_scan([], "aws", domain_timeout=5, enrich_from_aws=True)

    by_id = {r["resource_id"]: r for r in result["results"]}
    assert by_id["Z1"]["status"] == "pass"
    assert by_id["Z2"]["status"] == "error"
    assert by_id["Z2"]["discovery_error"] == "AccessDenied"
    assert exit_code == 1


def test_example_file_is_valid(route53):
    resources = route53.load_resources(route53.DEFAULT_RESOURCES_FILE)
    assert resources, "example.json should contain resources"
    for resource in resources:
        assert set(resource["checks"]) <= set(route53.CHECKS)

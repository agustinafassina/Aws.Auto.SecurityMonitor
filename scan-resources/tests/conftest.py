from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCAN_RESOURCES_DIR = Path(__file__).resolve().parents[1]
if str(SCAN_RESOURCES_DIR) not in sys.path:
    sys.path.insert(0, str(SCAN_RESOURCES_DIR))


def load_module(module: str):
    """Import scan-resources/<module>/scan_<module>.py (module dirs are not packages)."""
    path = SCAN_RESOURCES_DIR / module / f"scan_{module}.py"
    spec = importlib.util.spec_from_file_location(f"scan_{module}", path)
    loaded = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture
def route53():
    return load_module("route53")

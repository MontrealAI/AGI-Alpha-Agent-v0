# SPDX-License-Identifier: Apache-2.0
"""Keep a paper publication's three generated workers one exact byte edition."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("publication_refresh", ROOT / "scripts/refresh_capability_checkout.py")
assert SPEC is not None and SPEC.loader is not None
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)
WORKERS = (
    "docs/service-worker.js",
    "docs/assets/service-worker.js",
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)


def matching_profiles(records):
    raw = (ROOT / HELPER.CATALOG).read_bytes()
    return [extra for _, _, _, extra in HELPER._source_profiles(raw)
            if all(extra[name] == record for name, record in records.items())]


def test_published_workers_have_one_complete_source_bound_edition():
    records = {}
    for name in WORKERS:
        raw = (ROOT / name).read_bytes()
        records[name] = len(raw), hashlib.sha256(raw).hexdigest()
        size, digest = HELPER.PAPERS_20261026_EXTRA_FILES[name]
        assert HELPER._canonical(raw, digest, size, name) == raw
        assert HELPER._canonical(raw.replace(b"\n", b"\r\n"), digest, size, name) == raw
    assert matching_profiles(records) == [HELPER.PAPERS_20261026_EXTRA_FILES]


@pytest.mark.parametrize("name", WORKERS)
def test_preceding_and_published_worker_identities_cannot_form_a_mixed_edition(name):
    records = {path: HELPER.PAPERS_20261026_EXTRA_FILES[path] for path in WORKERS}
    records[name] = HELPER.STRATEGY_144_EXTRA_FILES[name]
    assert matching_profiles(records) == []


@pytest.mark.parametrize("name", WORKERS)
def test_published_worker_tampering_is_still_rejected(name):
    raw = (ROOT / name).read_bytes()
    size, digest = HELPER.PAPERS_20261026_EXTRA_FILES[name]
    with pytest.raises(ValueError, match="unexpected capability bytes"):
        HELPER._canonical(raw + b"// private edit\n", digest, size, name)

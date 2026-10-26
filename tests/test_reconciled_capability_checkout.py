# SPDX-License-Identifier: Apache-2.0
"""Keep the reconciled checkout repair closed to one complete public edition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "scripts/refresh_capability_checkout.py"))
WORKERS = (
    "docs/service-worker.js",
    "docs/assets/service-worker.js",
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js",
)


def test_reconciled_cache_profile_keeps_scientific_closure_and_bounds() -> None:
    old = HELPER["STRATEGY_144_EXTRA_FILES"]
    new = HELPER["RECONCILED_STRATEGY_144_EXTRA_FILES"]
    assert set(old) == set(new)
    assert {name for name in old if old[name] != new[name]} == set(WORKERS)
    for name in WORKERS:
        raw = (ROOT / name).read_bytes()
        assert (len(raw), hashlib.sha256(raw).hexdigest()) == new[name]
    result = HELPER["refresh"](ROOT)
    assert result["sourceHash"] == HELPER["ENTERPRISE_SOURCE_HASH"]
    assert result["checked"] == 61
    assert result["needsRefresh"] == []


@pytest.mark.parametrize("worker", WORKERS)
def test_reconciled_checkout_refuses_a_mixed_known_cache_before_writes(tmp_path: Path, worker: str) -> None:
    extra = HELPER["RECONCILED_STRATEGY_144_EXTRA_FILES"]
    catalog = json.loads((ROOT / HELPER["CATALOG"]).read_bytes())
    checkout = tmp_path / "checkout"
    for name in set(catalog["sources"]) | set(extra):
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes().replace(b"\n", b"\r\n"))
    fixture = json.loads((ROOT / "tests/fixtures/capability-checkout-foundry-140-workers.json").read_bytes())
    old = fixture["files"][worker]["text"].encode()
    assert (len(old), hashlib.sha256(old).hexdigest()) == HELPER["FOUNDRY_140_EXTRA_FILES"][worker]
    (checkout / worker).write_bytes(old.replace(b"\n", b"\r\n"))
    originals = {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()}
    backups = tmp_path / "backups"
    backups.mkdir()
    with pytest.raises(ValueError, match="Private or unexpected capability bytes"):
        HELPER["refresh"](checkout, apply=True, backup_parent=backups)
    assert not list(backups.iterdir())
    assert originals == {p.relative_to(checkout): p.read_bytes() for p in checkout.rglob("*") if p.is_file()}

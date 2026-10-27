# SPDX-License-Identifier: Apache-2.0
"""Accept only the complete reviewed reader patch worker edition."""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
import pytest
from scripts import refresh_capability_checkout as checkout

ROOT = Path(__file__).resolve().parents[1]


def test_reader_patch_exact_workers_and_mixed_or_unknown_rejection(tmp_path: Path) -> None:
    raw = (ROOT / "tests/fixtures/capability-checkout-paper-readers-1461-workers.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "9537d6f85cdbf220a1889e55057b3271fb512902fc30b8fe9a79a53cc176591f"
    fixture = json.loads(raw)
    assert fixture["version"] == "1.46.1"
    assert fixture["sourceBase"] == "80b345828f34fd8a6e592977dd17ef37141305f4"
    assert (
        fixture["generatorSha256"]
        == hashlib.sha256((ROOT / "scripts/build_service_worker.py").read_bytes()).hexdigest()
    )
    old = json.loads((ROOT / "tests/fixtures/capability-checkout-release-146-workers.json").read_bytes())
    catalog = json.loads((ROOT / checkout.CATALOG).read_bytes())
    bodies = {
        name: (ROOT / name).read_bytes()
        for name in set(catalog["sources"]) | set(checkout.PAPER_READERS_1461_EXTRA_FILES)
    }
    assert len(bodies) == 61
    assert set(fixture["files"]) == set(old["files"])
    for name, record in fixture["files"].items():
        body = record["text"].encode()
        bodies[name] = body
        assert (len(body), hashlib.sha256(body).hexdigest()) == checkout.PAPER_READERS_1461_EXTRA_FILES[name]
        assert (record["bytes"], record["sha256"]) == checkout.PAPER_READERS_1461_EXTRA_FILES[name]
        assert hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() == record["gitBlob"]
        assert (
            old["files"][name]["bytes"],
            old["files"][name]["sha256"],
        ) == checkout.PROTECTED_FLYWHEEL_146_EXTRA_FILES[name]
    for mask in range(8):
        selected = dict(bodies)
        for index, name in enumerate(fixture["files"]):
            selected[name] = (fixture if mask & (1 << index) else old)["files"][name]["text"].encode()
        root = tmp_path / str(mask)
        for name, body in selected.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        if mask in {0, 7}:
            result = checkout.refresh(root)
            assert result["checked"] == 61 and result["needsRefresh"] == [] and result["applied"] is False
        else:
            with pytest.raises(ValueError, match="unexpected capability bytes"):
                checkout.refresh(root)
        assert {name: (root / name).read_bytes() for name in selected} == selected
    for index, name in enumerate(fixture["files"]):
        root = tmp_path / f"unknown-{index}"
        selected = dict(bodies)
        selected[name] += b"\n// unreviewed change\n"
        for path_name, body in selected.items():
            path = root / path_name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
        with pytest.raises(ValueError, match="unexpected capability bytes"):
            checkout.refresh(root)
        assert {path_name: (root / path_name).read_bytes() for path_name in selected} == selected

# SPDX-License-Identifier: Apache-2.0
"""Received-pack controls keep extra files and rehashed corruptions visible."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from contrib.resilient_placement_delivery.__main__ import read_json, verify_pack
from contrib.resilient_placement_delivery.report import render_pack
from contrib.resilient_placement_delivery.runner import run_research


@pytest.fixture
def pack(tmp_path: Path) -> Path:
    source = (
        Path(__file__).resolve().parents[1] / "contrib/resilient_placement_delivery/examples/bilingual-publishing.json"
    )
    brief = json.loads(source.read_text())
    output = tmp_path / "private"
    evidence = run_research(brief, output)
    render_pack(brief, evidence["execution"], tmp_path / "pack")
    return tmp_path / "pack"


def test_exact_public_pack_verifies(pack: Path) -> None:
    assert verify_pack(pack) == {
        "verified_files": 5,
        "brief_id": "bilingual-publishing-01",
        "research_acceptance": True,
    }


@pytest.mark.parametrize("name", ["identity.key", "INCOMPLETE", "unexpected.py"])
def test_extra_private_or_incomplete_members_refuse(pack: Path, name: str) -> None:
    (pack / name).write_text("unexpected test member")
    with pytest.raises(ValueError, match="six public pack"):
        verify_pack(pack)


@pytest.mark.parametrize("name", ["plan.csv", "index.html", "delivery.json"])
def test_rehashed_false_exports_refuse(pack: Path, name: str) -> None:
    member = pack / name
    if name == "delivery.json":
        value = json.loads(member.read_text())
        value["plan"][0]["host"] = "unexecuted-host"
        member.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    else:
        member.write_text(member.read_text() + "misleading appended output\n")
    manifest = json.loads((pack / "manifest.json").read_text())
    raw = member.read_bytes()
    manifest["files"][name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    (pack / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    with pytest.raises(ValueError, match="canonical checked packaging"):
        verify_pack(pack)


def test_input_reader_refuses_duplicate_json_members(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous.json"
    path.write_text('{"price":1,"price":2}')
    with pytest.raises(ValueError):
        read_json(path)

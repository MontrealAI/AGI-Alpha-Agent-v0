# SPDX-License-Identifier: Apache-2.0
"""Keep the published deployment archive exact and free of local operator files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import pytest

from scripts.package_agent_release import package_mainnet_record

ROOT = Path(__file__).resolve().parents[1]
RECORD = Path("deployments/ethereum-mainnet/2026-10-11")


def test_mainnet_archive_preserves_evidence_and_excludes_unlisted_files(tmp_path: Path) -> None:
    checkout = tmp_path / "source"
    shutil.copytree(ROOT / RECORD, checkout / RECORD)
    verifier = checkout / "tests/contracts/scripts/mainnet-record.js"
    verifier.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "tests/contracts/scripts/mainnet-record.js", verifier)
    (checkout / RECORD / "unlisted-private-file.txt").write_text("must not be packaged")
    output = tmp_path / "output"
    output.mkdir()
    (output / "MAINNET_DEPLOYMENT.md").write_text("reviewed owner guide")
    target = package_mainnet_record(checkout, output, "1.26.1")
    manifest = json.loads((ROOT / RECORD / "manifest.json").read_text())
    with zipfile.ZipFile(target) as archive:
        assert len(archive.namelist()) == len(manifest["files"]) + 3
        assert not any("private-file" in name for name in archive.namelist())
        for name, expected in manifest["files"].items():
            assert hashlib.sha256(archive.read(f"ascension-ethereum-mainnet-2026-10-11/{name}")).hexdigest() == expected
        assert b"../MAINNET_DEPLOYMENT.md" in archive.read("ascension-ethereum-mainnet-2026-10-11/README.md")
    with pytest.raises(FileExistsError):
        package_mainnet_record(checkout, output, "1.26.1")


def test_mainnet_archive_rejects_modified_compiler_evidence(tmp_path: Path) -> None:
    shutil.copytree(ROOT / RECORD, tmp_path / RECORD)
    verifier = tmp_path / "tests/contracts/scripts/mainnet-record.js"
    verifier.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "tests/contracts/scripts/mainnet-record.js", verifier)
    with (tmp_path / RECORD / "compiler-input.json").open("a") as stream:
        stream.write(" ")
    output = tmp_path / "output"
    output.mkdir()
    with pytest.raises(ValueError, match="digest differs"):
        package_mainnet_record(tmp_path, output, "1.26.1")

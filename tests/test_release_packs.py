# SPDX-License-Identifier: Apache-2.0
"""Adversarial distribution tests exercise actual pack bytes and atomic restores."""

from __future__ import annotations

import hashlib
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from scripts.build_service_worker import gather_assets
from scripts import release_packs
from scripts.release_packs import MAX_ASSET_BYTES, classify, pack, require_asset_limits, restore


@pytest.fixture
def distribution(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("<h1>Offline bounded rehearsal</h1>")
    (source / "models").mkdir()
    (source / "models/model.onnx").write_bytes(bytes(range(256)) * 80)
    (source / "research").mkdir()
    (source / "research/original.pdf").write_bytes(b"preserved source\n")
    manifest = pack(source, tmp_path / "packs", "site", commit="a" * 40, version="1.24.0", limit=4096)
    return source, manifest


def test_split_roundtrip_is_complete_deterministic_and_bounded(distribution, tmp_path: Path) -> None:
    source, manifest = distribution
    data = json.loads(manifest.read_bytes())
    assert len(data["packs"]) > 3
    assert all((manifest.parent / item["name"]).stat().st_size <= 4096 for item in data["packs"])
    destination = tmp_path / "restored"
    assert restore(manifest, destination)["files"] == 3
    for item in source.rglob("*"):
        if item.is_file():
            assert (destination / item.relative_to(source)).read_bytes() == item.read_bytes()
    other = pack(source, tmp_path / "second", "site", commit="a" * 40, version="1.24.0", limit=4096)
    assert manifest.read_bytes() == other.read_bytes()
    assert [item.read_bytes() for item in sorted(manifest.parent.glob("*.zip"))] == [
        item.read_bytes() for item in sorted(other.parent.glob("*.zip"))
    ]


def test_core_restore_needs_no_optional_model_or_research_pack(distribution, tmp_path: Path) -> None:
    _, manifest = distribution
    data = json.loads(manifest.read_bytes())
    for item in data["packs"]:
        if item["group"] != "core":
            (manifest.parent / item["name"]).unlink()
    destination = tmp_path / "core"
    restore(manifest, destination, groups=["core"])
    assert (destination / "index.html").is_file()
    assert not (destination / "models").exists()


def test_core_preserves_every_gallery_precache_dependency(tmp_path: Path) -> None:
    docs = Path(__file__).resolve().parents[1] / "docs"
    assert all(classify(name) == "core" for name in gather_assets(docs))
    source = tmp_path / "source"
    preview = source / "presentation/assets/preview.svg"
    preview.parent.mkdir(parents=True)
    preview.write_text("<svg></svg>")
    manifest = pack(source, tmp_path / "packs", "site", commit="a" * 40, version="1.24.0")
    destination = tmp_path / "restored"
    restore(manifest, destination, groups=["core"])
    assert (destination / "presentation/assets/preview.svg").read_bytes() == preview.read_bytes()


@pytest.mark.parametrize("damage", ["checksum", "traversal", "duplicate", "size", "unknown", "group", "file_digest"])
def test_damaged_import_never_promotes_state(distribution, tmp_path: Path, damage: str) -> None:
    _, manifest = distribution
    data = json.loads(manifest.read_bytes())
    if damage == "checksum":
        (manifest.parent / data["packs"][0]["name"]).write_bytes(b"corrupt")
    elif damage == "traversal":
        data["files"][0]["path"] = "../escaped"
    elif damage == "duplicate":
        data["files"].append(data["files"][0])
    elif damage == "size":
        data["total_bytes"] = MAX_ASSET_BYTES * 100
    elif damage == "unknown":
        data["trust_me"] = True
    elif damage == "group":
        data["files"][0]["group"] = "models"
    else:
        data["files"][0]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        restore(manifest, tmp_path / "destination")
    assert not (tmp_path / "destination").exists()
    assert not (tmp_path / "escaped").exists()


def test_duplicate_json_keys_rejected(distribution, tmp_path: Path) -> None:
    _, manifest = distribution
    manifest.write_text(manifest.read_text().replace('"schema":', '"schema":"forged","schema":'))
    with pytest.raises(ValueError, match="Duplicate"):
        restore(manifest, tmp_path / "destination")


def test_link_in_archive_rejected_even_with_updated_manifest(distribution, tmp_path: Path) -> None:
    _, manifest = distribution
    data = json.loads(manifest.read_bytes())
    item = next(pack for pack in data["packs"] if pack["group"] == "core")
    path = manifest.parent / item["name"]
    with zipfile.ZipFile(path, "w") as archive:
        entry = zipfile.ZipInfo("index.html")
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(entry, "../../private")
    item.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="links"):
        restore(manifest, tmp_path / "destination")
    assert not (tmp_path / "destination").exists()


def test_existing_state_is_never_replaced(distribution, tmp_path: Path) -> None:
    _, manifest = distribution
    target = tmp_path / "existing"
    target.mkdir()
    (target / "keep").write_text("operator data")
    with pytest.raises(ValueError, match="already exists"):
        restore(manifest, target)
    assert (target / "keep").read_text() == "operator data"


@pytest.mark.parametrize("damage", ["missing", "corrupt", "existing"])
def test_restore_cli_explains_download_and_destination_errors_without_state_loss(
    distribution, tmp_path: Path, damage: str
):
    _, manifest = distribution
    destination = tmp_path / "restored site"
    if damage == "missing":
        manifest.unlink()
    elif damage == "corrupt":
        data = json.loads(manifest.read_bytes())
        (manifest.parent / data["packs"][0]["name"]).write_bytes(b"corrupt")
    else:
        destination.mkdir()
        (destination / "keep.txt").write_text("operator data")
    result = subprocess.run(
        [
            sys.executable,
            release_packs.__file__,
            "restore",
            "--manifest",
            str(manifest),
            "--destination",
            str(destination),
        ],
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 1
    assert "Restore stopped:" in result.stderr and "restore --help" in result.stderr
    assert "Traceback" not in result.stderr and result.stdout == ""
    if damage == "existing":
        assert (destination / "keep.txt").read_text() == "operator data"
    else:
        assert not destination.exists()


def test_restore_cli_keeps_machine_readable_success_and_exact_contents(distribution, tmp_path: Path) -> None:
    source, manifest = distribution
    destination = tmp_path / "restored site"
    result = subprocess.run(
        [
            sys.executable,
            release_packs.__file__,
            "restore",
            "--manifest",
            str(manifest),
            "--destination",
            str(destination),
            "--groups",
            "core",
        ],
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"commit": "a" * 40, "version": "1.24.0", "groups": ["core"], "files": 1}
    assert (destination / "index.html").read_bytes() == (source / "index.html").read_bytes()
    assert not (destination / "models").exists()


def test_oversized_final_asset_blocks_publication(tmp_path: Path) -> None:
    with (tmp_path / "large").open("wb") as stream:
        stream.truncate(MAX_ASSET_BYTES + 1)
    with pytest.raises(ValueError, match="exceeds"):
        require_asset_limits(tmp_path)


def test_zip_source_preserves_original_member_paths(tmp_path: Path) -> None:
    source = tmp_path / "browser.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("index.html", "hello")
        archive.writestr("assets/model.json", "{}")
    manifest = pack(source, tmp_path / "packs", "browser", commit="b" * 40, version="1.24.0")
    restore(manifest, tmp_path / "browser")
    assert (tmp_path / "browser/assets/model.json").read_text() == "{}"


@pytest.mark.parametrize("name", ["../escape", "/absolute", "a\\b", "a/./b", "a//b", "NUL.txt", "folder./file"])
def test_ambiguous_cross_platform_source_paths_are_rejected(tmp_path: Path, name: str) -> None:
    source = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(name, "unsafe")
    with pytest.raises(ValueError):
        pack(source, tmp_path / "packs", "unsafe", commit="a" * 40, version="1.24.0")


def test_public_successor_report_cannot_substitute_a_different_revision() -> None:
    from scripts.successor_evidence import REQUIRED_CHECKS, SCHEMA, verify_report

    report = {
        "schema": SCHEMA,
        "passed": True,
        "commit": "a" * 40,
        "version": "1.24.0",
        "origin": "https://site/",
        "browser_errors": [],
        "checks": sorted(REQUIRED_CHECKS),
    }
    verify_report(report, "a" * 40, "1.24.0", "https://site/")
    for key, replacement in (
        ("commit", "b" * 40),
        ("version", "1.23.3"),
        ("checks", []),
        ("browser_errors", ["error"]),
        ("passed", False),
    ):
        with pytest.raises(ValueError):
            verify_report({**report, key: replacement}, "a" * 40, "1.24.0", "https://site/")


@pytest.mark.parametrize("version", ["1.24.1", "1.25.0"])
def test_successor_publication_requires_homepage_entry_from_the_discoverability_patch(version: str) -> None:
    from scripts.successor_evidence import REQUIRED_CHECKS, SCHEMA, verify_report

    report = {
        "schema": SCHEMA,
        "passed": True,
        "commit": "a" * 40,
        "version": version,
        "origin": "https://site/",
        "browser_errors": [],
        "checks": sorted(REQUIRED_CHECKS),
    }
    verify_report(report, "a" * 40, version, "https://site/")
    without_homepage = {**report, "checks": sorted(REQUIRED_CHECKS - {"homepage-entry"})}
    with pytest.raises(ValueError, match="every required journey"):
        verify_report(without_homepage, "a" * 40, version, "https://site/")
    # Published 1.24.0 evidence predates this additional browser journey.
    legacy = {**without_homepage, "version": "1.24.0"}
    verify_report(legacy, "a" * 40, "1.24.0", "https://site/")

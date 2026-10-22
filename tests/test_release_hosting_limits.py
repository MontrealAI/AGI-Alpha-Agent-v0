# SPDX-License-Identifier: Apache-2.0
"""Remove the accidental project cap without weakening bounded release transport."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path

import pytest

from scripts import release_packs


def reported_size(monkeypatch: pytest.MonkeyPatch, path: Path, size: int) -> None:
    """Exercise large metadata boundaries while hashing only a real tiny fixture."""
    original = Path.stat

    def stat(target: Path, *, follow_symlinks: bool = True) -> os.stat_result:
        result = original(target, follow_symlinks=follow_symlinks)
        if target == path:
            fields = list(result)
            fields[6] = size
            return os.stat_result(fields)
        return result

    monkeypatch.setattr(Path, "stat", stat)


@pytest.mark.parametrize("size", [450_000_001, (2**31) - 2, (2**31) - 1])
def test_hosting_bound_accepts_assets_above_the_removed_project_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    path = tmp_path / "validation.zip"
    raw = b"every original evidence byte"
    path.write_bytes(raw)
    reported_size(monkeypatch, path, size)
    assert release_packs.require_asset_limits(tmp_path) == [
        {"name": path.name, "bytes": size, "sha256": hashlib.sha256(raw).hexdigest()}
    ]
    assert path.read_bytes() == raw


@pytest.mark.parametrize("size", [2**31, (2**31) + 1])
def test_hosting_bound_rejects_two_gib_and_larger_before_hashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    path = tmp_path / "validation.zip"
    path.write_bytes(b"retained")
    reported_size(monkeypatch, path, size)
    with pytest.raises(ValueError, match="exceeds 2147483647"):
        release_packs.require_asset_limits(tmp_path)


@pytest.mark.parametrize("limit", [450_000_000, 450_000_001, (2**31) - 1])
def test_old_and_new_pack_manifests_restore_identical_bytes(tmp_path: Path, limit: int) -> None:
    source = tmp_path / "source"
    source.mkdir()
    raw = b"original source bytes\r\nremain exact\x00"
    (source / "capture.bin").write_bytes(raw)
    path = release_packs.pack(source, tmp_path / "packs", "evidence", commit="a" * 40, version="1.38.0", limit=limit)
    manifest = json.loads(path.read_bytes())
    assert manifest["schema"] == "agialpha.release-packs.v1"
    assert manifest["max_asset_bytes"] == limit
    identity = release_packs.restore(path, tmp_path / "restored")
    assert identity["commit"] == "a" * 40
    assert (tmp_path / "restored/capture.bin").read_bytes() == raw
    manifest["max_asset_bytes"] = 2**31
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="size ceiling"):
        release_packs.restore(path, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_new_default_and_pack_argument_use_only_the_hosting_bound(tmp_path: Path) -> None:
    assert release_packs.MAX_ASSET_BYTES == (2**31) - 1
    source = tmp_path / "source"
    source.mkdir()
    (source / "capture").write_bytes(b"exact")
    path = release_packs.pack(source, tmp_path / "packs", "evidence", commit="b" * 40, version="1.38.0")
    assert json.loads(path.read_bytes())["max_asset_bytes"] == (2**31) - 1
    with pytest.raises(ValueError, match="outside supported bounds"):
        release_packs.pack(source, tmp_path / "refused", "evidence", commit="b" * 40, version="1.38.0", limit=2**31)


def test_pack_reader_still_requests_at_most_64_mib(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    source.mkdir()
    path = source / "capture"
    path.write_bytes(b"small physical fixture")
    reported_size(monkeypatch, path, 64 * 1024 * 1024 + 1)
    requests = []

    class StopAfterRequest(io.BytesIO):
        def read(self, size: int | None = -1) -> bytes:
            requests.append(size)
            raise RuntimeError("observed bounded read without allocating a large fixture")

    monkeypatch.setattr(release_packs, "open_binary", lambda path: StopAfterRequest())
    with pytest.raises(RuntimeError, match="observed bounded read"):
        release_packs.pack(source, tmp_path / "packs", "evidence", commit="a" * 40, version="1.38.0")
    assert requests == [64 * 1024 * 1024]


@pytest.mark.parametrize("size,read_allowed", [(64 * 1024 * 1024, True), (64 * 1024 * 1024 + 1, False)])
def test_public_manifest_limit_is_enforced_before_reading_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int, read_allowed: bool
) -> None:
    from scripts import finalize_pages_release

    version = "1.38.0"
    local = tmp_path / f"alpha-agent-v{version}-validation.zip"
    local.write_bytes(b"original local evidence")
    manifest = {"commit": "a" * 40, "version": version}
    record = {
        "schema": "agialpha.validation-evidence.v1",
        **manifest,
        "local": finalize_pages_release._local_validation(tmp_path, manifest),
        "public": {},
    }
    path = tmp_path / f"alpha-agent-v{version}-public-validation-packs.json"
    path.write_bytes(b"{}")
    reported_size(monkeypatch, path, size)
    original = Path.read_bytes

    def read(target: Path) -> bytes:
        if target == path:
            raise RuntimeError("manifest reader reached")
        return original(target)

    monkeypatch.setattr(Path, "read_bytes", read)
    exception = RuntimeError if read_allowed else ValueError
    message = "manifest reader reached" if read_allowed else "Public validation pack manifest"
    with pytest.raises(exception, match=message):
        finalize_pages_release.verify_public_validation(
            tmp_path, tmp_path / "evidence", {**manifest, "validation_evidence": record}
        )

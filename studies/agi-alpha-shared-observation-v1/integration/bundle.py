# SPDX-License-Identifier: Apache-2.0
"""Package and verify the exact two-file retained capability for research transfer."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

MAX_BUNDLE_BYTES = 2_000_000
PAYLOAD_NAMES = ("compiler.py", "sensor_profile.json")


def sha256(data: bytes) -> str:
    """Return the exact content identity."""
    return hashlib.sha256(data).hexdigest()


def regular_bytes(path: Path) -> bytes:
    """Read a bounded ordinary file without accepting a symlink."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("ordinary retained source file required")
    data = path.read_bytes()
    if len(data) > MAX_BUNDLE_BYTES:
        raise ValueError("retained file exceeds the research bound")
    return data


def make_bundle(compiler: Path, profile: Path, target: Path) -> dict[str, Any]:
    """Create deterministic source bytes without changing the existing lifecycle."""
    if target.exists():
        raise ValueError("bundle output must be new")
    contents = {"compiler.py": regular_bytes(compiler), "sensor_profile.json": regular_bytes(profile)}
    json.loads(contents["sensor_profile.json"])
    manifest = {
        "schema": "shared-observation-retained-bundle/v1",
        "provenance": "Researcher-constructed instrument; profile origin is recorded in study evidence.",
        "rights": "Apache-2.0 study sources; public input data retain their own licenses.",
        "scope": "Bounded research observation-design computation with fresh mission checking.",
        "authority": "NO_LIVE_ENS_OR_PRODUCTION_AUTHORITY",
        "files": [
            {"name": name, "bytes": len(data), "sha256": sha256(data)} for name, data in sorted(contents.items())
        ],
    }
    contents["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(contents.items()):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.external_attr = 0o100644 << 16
            entry.create_system = 3
            archive.writestr(entry, data)
    raw = buffer.getvalue()
    if len(raw) > MAX_BUNDLE_BYTES:
        raise ValueError("bundle exceeds the unchanged lifecycle bridge bound")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return {"sha256": sha256(raw), "bytes": len(raw), "manifest": manifest}


def read_bundle(path: Path, expected_sha256: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Validate exact bytes and a finite archive before any recipient execution."""
    raw = regular_bytes(path)
    if sha256(raw) != expected_sha256:
        raise ValueError("received bundle differs from the retained artifact")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if sorted(names) != ["compiler.py", "manifest.json", "sensor_profile.json"]:
            raise ValueError("bundle must contain exactly the declared ordinary payload files")
        if any(entry.file_size > MAX_BUNDLE_BYTES for entry in entries):
            raise ValueError("unpacked file exceeds research bound")
        if sum(entry.file_size for entry in entries) > MAX_BUNDLE_BYTES:
            raise ValueError("unpacked bundle exceeds research bound")
        if any(entry.compress_type != zipfile.ZIP_STORED or entry.is_dir() for entry in entries):
            raise ValueError("unexpected archive representation")
        payload = {name: archive.read(name) for name in names}
    manifest = json.loads(payload.pop("manifest.json"))
    if manifest.get("schema") != "shared-observation-retained-bundle/v1":
        raise ValueError("unsupported retained bundle schema")
    rows = manifest.get("files")
    if not isinstance(rows, list) or len(rows) != 2 or sorted(row.get("name", "") for row in rows) != list(PAYLOAD_NAMES):
        raise ValueError("unsupported retained file inventory")
    for row in rows:
        data = payload[row["name"]]
        if row["bytes"] != len(data) or row["sha256"] != sha256(data):
            raise ValueError("retained payload identity mismatch")
    json.loads(payload["sensor_profile.json"])
    return manifest, payload


def unpack_bundle(path: Path, expected_sha256: str, destination: Path) -> dict[str, Any]:
    """Write verified bytes into a new, recipient-owned directory."""
    manifest, payload = read_bundle(path, expected_sha256)
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in payload.items():
        (destination / name).write_bytes(data)
    return manifest

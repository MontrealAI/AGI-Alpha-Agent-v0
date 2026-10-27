# SPDX-License-Identifier: Apache-2.0
"""Create deterministic, lossless preservation packages without changing originals."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
import gzip
import hashlib
import json
import os
import re
import stat
import zipfile
import zlib

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
V3 = REPO / "studies/agi-alpha-economic-construction-v3"
V4_PREFIX = "studies/agi-alpha-opportunity-discovery-v4"
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".venv", "venv"}


def sha(data: bytes) -> str:
    """Return the exact byte identity."""
    return hashlib.sha256(data).hexdigest()


def write_exact(path: Path, data: bytes) -> None:
    """Create only missing files; preserve an identical existing package."""
    if path.is_symlink():
        raise ValueError("Refuse symlink package target: " + str(path))
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("Refuse to replace a different existing package: " + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)


def json_bytes(value: Any) -> bytes:
    """Serialize manifest metadata deterministically."""
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def ordinary_files(root: Path) -> tuple[list[Path], list[str]]:
    """List source files while explicitly excluding environments and caches."""
    files, excluded = [], []
    for directory, directories, names in os.walk(root, followlinks=False):
        for name in sorted(list(directories)):
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError("Unexpected symlink directory: " + str(path))
            if name in SKIP_DIRS or name.startswith("venv_"):
                directories.remove(name)
                excluded.append(str(path.relative_to(root)))
        for name in sorted(names):
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Nonordinary input file: " + str(path))
            if path.suffix in {".pyc", ".pyo"}:
                excluded.append(str(path.relative_to(root)))
                continue
            if name.startswith(".env") or path.suffix in {".pem", ".key", ".p12", ".pfx"}:
                raise ValueError("Potential secret requires explicit review: " + str(path))
            files.append(path)
    return sorted(files), sorted(excluded)


def make_zip(path: Path, records: list[tuple[str, str, bytes, int]], provenance: dict[str, Any]) -> dict[str, Any]:
    """Package only explicitly selected regular files, with fixed ZIP metadata."""
    output = BytesIO()
    entries = []
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for member, target, data, mode in sorted(records):
            info = zipfile.ZipInfo(member, date_time=(2026, 10, 27, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
            entries.append({"member": member, "path": target, "bytes": len(data), "sha256": sha(data), "mode": mode})
    data = output.getvalue()
    write_exact(path, data)
    manifest = {
        "schema": "lossless-explicit-zip-members/v1",
        "archive": str(path.relative_to(STUDY)),
        "archive_sha256": sha(data),
        "archive_bytes": len(data),
        "raw_bytes": sum(x["bytes"] for x in entries),
        "member_count": len(entries),
        "entries": entries,
        "provenance": provenance,
        "zip_policy": "sorted regular members, fixed 2026-10-27 UTC date fields, deflate level 9",
    }
    manifest_path = path.with_suffix(".manifest.json")
    write_exact(manifest_path, json_bytes(manifest))
    return {
        "archive": str(path.relative_to(STUDY)),
        "archive_sha256": sha(data),
        "archive_bytes": len(data),
        "manifest": str(manifest_path.relative_to(STUDY)),
        "manifest_sha256": sha(json_bytes(manifest)),
        "members": len(entries),
    }


def main() -> None:
    """Preserve the entire old fixture and only compress selected generated outputs."""
    v3_files, excluded = ordinary_files(V3)
    snapshots = [(path, path.read_bytes()) for path in v3_files]
    records = [
        (
            str(path.relative_to(V3)),
            "studies/agi-alpha-economic-construction-v3/" + str(path.relative_to(V3)),
            raw,
            0o755 if path.stat().st_mode & 0o111 else 0o644,
        )
        for path, raw in snapshots
    ]
    archives = [
        make_zip(
            STUDY / "historical/v3_fixture.zip",
            records,
            {
                "kind": "complete-preserved-v3-study",
                "source": "studies/agi-alpha-economic-construction-v3",
                "excluded": excluded,
                "source_mutations": 0,
                "secret_review": "No credential filenames, private-key blocks or nonempty credential JSON fields found in bounded local review; no universal secret-detection claim.",
                "scope": "Earlier microgrid fixture and full unsuccessful/revised history; not the v4 flagship",
            },
        )
    ]
    inputs = json.loads((STUDY / "evaluation/protected/input_manifest.json").read_text())
    if len(inputs) != 10:
        raise ValueError("Expected the ten already selected public evaluation inputs")
    records = []
    for item in inputs:
        relative = "evaluation/protected/inputs/" + item["file"]
        raw = (STUDY / relative).read_bytes()
        if sha(raw) != item["sha256"] or len(raw) != item["bytes"]:
            raise ValueError("Changed public evaluation member: " + relative)
        records.append((relative, V4_PREFIX + "/" + relative, raw, 0o644))
    for relative in ["evaluation/SOURCE_NOTICES.md", "evaluation/protected/input_manifest.json"]:
        records.append((relative, V4_PREFIX + "/" + relative, (STUDY / relative).read_bytes(), 0o644))
    archives.append(
        make_zip(
            STUDY / "data/public_evaluation_inputs.zip",
            records,
            {
                "kind": "ten-exact-public-NIST-evaluation-inputs-plus-notices-and-manifest",
                "original_bytes_modified": False,
                "upstream_sources": inputs,
                "official_archive_fallback": "evaluation/restore_inputs.py",
                "not_observed_customer_data": True,
            },
        )
    )

    # Keep the already preserved Plate package unchanged; bind its members for
    # the same safe restoration path instead of executing any source script.
    plate_path = STUDY / "data/development/plate_public_inputs.zip"
    plate_entries = []
    with zipfile.ZipFile(plate_path) as archive:
        for info in archive.infolist():
            raw = archive.read(info)
            if "/" in info.filename:
                raise ValueError("Expected original flat Plate archive")
            subdir = "" if info.filename.endswith("NOTICE.md") else "inputs/"
            target = V4_PREFIX + "/data/development/" + subdir + info.filename
            plate_entries.append(
                {"member": info.filename, "path": target, "bytes": len(raw), "sha256": sha(raw), "mode": 0o644}
            )
    plate_manifest = {
        "schema": "lossless-explicit-zip-members/v1",
        "archive": "data/development/plate_public_inputs.zip",
        "archive_sha256": sha(plate_path.read_bytes()),
        "archive_bytes": plate_path.stat().st_size,
        "entries": plate_entries,
        "member_count": len(plate_entries),
        "raw_bytes": sum(x["bytes"] for x in plate_entries),
        "provenance": "Existing unchanged Plate development package, including both NIST notices",
    }
    plate_manifest_path = STUDY / "reproduction/plate_restore.manifest.json"
    write_exact(plate_manifest_path, json_bytes(plate_manifest))
    archives.append(
        {
            "archive": plate_manifest["archive"],
            "archive_sha256": plate_manifest["archive_sha256"],
            "archive_bytes": plate_manifest["archive_bytes"],
            "manifest": str(plate_manifest_path.relative_to(STUDY)),
            "manifest_sha256": sha(json_bytes(plate_manifest)),
            "members": len(plate_entries),
        }
    )

    compressed = []
    files, _ = ordinary_files(STUDY)
    for path in files:
        relative = str(path.relative_to(STUDY))
        lower = relative.lower()
        if relative.split("/")[0] not in {"evaluation", "integration", "economics", "data", "expertise"}:
            continue
        if path.suffix not in {".json", ".log"} or path.stat().st_size < 65536:
            continue
        if any(word in lower for word in ["failed_candidates", "/history/", "summary", "freeze", "manifest"]):
            continue
        raw = path.read_bytes()
        # These flags are reviewed without printing potentially sensitive values.
        if re.search(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", raw):
            raise ValueError("Private key block requires review: " + relative)
        buffer = BytesIO()
        with gzip.GzipFile(filename="", fileobj=buffer, mode="wb", mtime=0, compresslevel=9) as stream:
            stream.write(raw)
        packed = buffer.getvalue()
        packed_relative = "reproduction/packed/" + sha(raw) + ".gz"
        write_exact(STUDY / packed_relative, packed)
        compressed.append(
            {
                "path": V4_PREFIX + "/" + relative,
                "bytes": len(raw),
                "sha256": sha(raw),
                "gzip": packed_relative,
                "gzip_bytes": len(packed),
                "gzip_sha256": sha(packed),
                "mode": 0o644,
            }
        )
    manifest = {
        "schema": "agi-alpha-reproduction-restore/v1",
        "repository_parent": "231834269599d85e49cfe1ca9917a1a874522d44",
        "inherited_bridge_commit": "80b345828f34fd8a6e592977dd17ef37141305f4",
        "source_tree": V4_PREFIX,
        "archives": archives,
        "compressed_files": compressed,
        "compression": {"gzip_mtime": 0, "gzip_filename": "", "level": 9, "zlib_version": zlib.ZLIB_VERSION},
        "preservation": "Raw originals remain local. Restoration is exact byte reconstruction, not experiment execution.",
        "rerun_status": "Any rerun is reproduction of known cases, not fresh prospective confirmation.",
    }
    write_exact(STUDY / "reproduction/RESTORE_MANIFEST.json", json_bytes(manifest))
    exclusions = ["/" + item["path"].removeprefix(V4_PREFIX + "/") for item in compressed]
    exclusions += ["/evaluation/protected/inputs/" + item["file"] for item in inputs]
    exclusions += [
        "/data/development/inputs/" + item["file"]
        for item in json.loads((STUDY / "data/development/input_manifest.json").read_text())
    ]
    ignore = "\n".join(
        [
            "# Exact generated bytes are restored by prepare_reproduction.py; originals remain local.",
            "# No source code, readable summary, notice or failed candidate is excluded here.",
            *sorted(exclusions),
            "# Disposable interpreter state and the original pilot installation environments.",
            "**/__pycache__/",
            "/dossier/runtime_pilot/venv_current/",
            "/dossier/runtime_pilot/venv_reported/",
            "# Keep the explicit compact preservation assets available to Git.",
            "!/historical/v3_fixture.zip",
            "!/data/public_evaluation_inputs.zip",
            "!/reproduction/packed/*.gz",
            "",
        ]
    )
    write_exact(STUDY / ".gitignore", ignore.encode())
    for path, raw in snapshots:
        if path.read_bytes() != raw:
            raise ValueError("Original v3 file changed during packaging: " + str(path))
    unique = {entry["gzip"]: entry["gzip_bytes"] for entry in compressed}
    print(
        json.dumps(
            {
                "v3_files": len(snapshots),
                "v3_archive": archives[0],
                "public_archive": archives[1],
                "compressed_raw_files": len(compressed),
                "compressed_raw_bytes": sum(x["bytes"] for x in compressed),
                "unique_gzip_objects": len(unique),
                "unique_gzip_bytes": sum(unique.values()),
                "source_mutations": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

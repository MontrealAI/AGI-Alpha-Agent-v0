# SPDX-License-Identifier: Apache-2.0
"""Prospective protected generator and output oracle; no candidate imports."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import zipfile


SCHEMA = "software-capability-foundry/confirmation-v1"
CASE_COUNT = 24
COUNTS = (8, 24, 64, 128)
SOURCE_PREFIXES = ("alpha_factory_v1/", "scripts/", "tests/")
SOURCE_SUFFIXES = {".py", ".md", ".json", ".mjs", ".js", ".txt", ".yml"}


def command(repo: Path, *args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", "--no-replace-objects", "--literal-pathspecs", "-C", str(repo), *args],
        input=data,
        capture_output=True,
        check=True,
        timeout=30,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Capability Foundry fixture generator",
            "GIT_AUTHOR_EMAIL": "research-fixtures@example.invalid",
            "GIT_COMMITTER_NAME": "Capability Foundry fixture generator",
            "GIT_COMMITTER_EMAIL": "research-fixtures@example.invalid",
            "GIT_AUTHOR_DATE": "2026-10-25T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-10-25T00:00:00+00:00",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
        },
    )
    return result.stdout


def eligible_sources(repo: Path, commit: str) -> list[dict[str, str | int]]:
    if re.fullmatch("[0-9a-f]{40}", commit) is None:
        raise ValueError("Pinned exact source commit required")
    if command(repo, "cat-file", "-t", commit).strip() != b"commit":
        raise ValueError("Pinned source is not a commit")
    values = []
    for record in command(repo, "ls-tree", "-r", "-z", "-l", commit).split(b"\0"):
        if not record:
            continue
        meta, raw = record.split(b"\t", 1)
        mode, kind, oid, size = meta.split()
        name = raw.decode("utf-8")
        if (
            mode in {b"100644", b"100755"}
            and kind == b"blob"
            and name.startswith(SOURCE_PREFIXES)
            and Path(name).suffix in SOURCE_SUFFIXES
            and not any(part in name.split("/") for part in ("archive", "vendor", "node_modules", "fixtures"))
            and size.isdigit()
            and 16 <= int(size) <= 100_000
        ):
            values.append({"path": name, "oid": oid.decode(), "bytes": int(size)})
    if len(values) < 128:
        raise ValueError("Insufficient independently selected public source pool")
    return sorted(values, key=lambda value: str(value["path"]))


def _write_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(files):
            entry = zipfile.ZipInfo(name, date_time=(2026, 10, 25, 0, 0, 0))
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, files[name])


def generate(source: Path, commit: str, destination: Path, seed: str) -> dict:
    if re.fullmatch("[0-9a-f]{64}", seed) is None:
        raise ValueError("The confirmation seed must be a fresh 256-bit hexadecimal value")
    if destination.exists():
        raise ValueError("Confirmation generation never overwrites an existing evidence boundary")
    source_pool = eligible_sources(source, commit)
    rng = random.Random(int(seed, 16))
    chosen = rng.sample(source_pool, 128)
    content = {str(row["oid"]): command(source, "cat-file", "blob", str(row["oid"])) for row in chosen}
    destination.mkdir(parents=True)
    cases = []
    for index in range(CASE_COUNT):
        case_dir = destination / f"case-{index:02d}"
        repo = case_dir / "repository"
        repo.mkdir(parents=True)
        command(repo, "init", "--quiet", "--object-format=sha1", "-b", "fixture")
        count = COUNTS[index % len(COUNTS)]
        repeated_fraction = (0.0, 0.25, 0.5)[(index // len(COUNTS)) % 3]
        unique = max(1, count - int(count * repeated_fraction))
        selected = rng.sample(chosen, unique)
        selected += rng.choices(selected, k=count - unique)
        rng.shuffle(selected)
        expected: dict[str, bytes] = {}
        provenance = {}
        for item, row in enumerate(selected):
            folder = ("sources", "changed layout", "étude", "nested/a/b")[(index + item) % 4]
            suffix = Path(str(row["path"])).suffix
            name = f"{folder}/{rng.getrandbits(64):016x}_{item:03d}{suffix}"
            body = content[str(row["oid"])]
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            expected[name] = body
            provenance[name] = row
        command(repo, "add", "--all")
        command(repo, "commit", "--quiet", "-m", "Prospective source-derived confirmation fixture")
        case_commit = command(repo, "rev-parse", "HEAD").decode().strip()
        names = sorted(expected)
        archive_files = dict(expected)
        drift = index % 5
        changed, missing, extra = [], [], []
        if drift in {1, 4}:
            name = names[0]
            archive_files[name] += b"\nCONTROLLED CONFIRMATION DRIFT\n"
            changed.append(name)
        if drift in {2, 4}:
            name = names[-1]
            del archive_files[name]
            missing.append(name)
        if drift in {3, 4}:
            name = "unexpected/public-note.txt"
            archive_files[name] = b"Extra package member: deliberately invalid against committed inventory.\n"
            extra.append(name)
        _write_zip(case_dir / "archive.zip", archive_files)
        oracle = {
            "files": {
                name: {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
                for name, body in sorted(expected.items())
            },
            "drift": {"changed": sorted(changed), "missing": sorted(missing), "extra": sorted(extra)},
            "source_provenance": provenance,
        }
        (case_dir / "oracle.json").write_text(json.dumps(oracle, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        # A working-tree shortcut must fail while the exact commit remains correct.
        (repo / names[0]).write_bytes(b"UNCOMMITTED WORKTREE DECOY\n")
        rng.shuffle(names)
        cases.append(
            {
                "id": f"case-{index:02d}",
                "repository": f"case-{index:02d}/repository",
                "commit": case_commit,
                "paths": names,
                "archive": f"case-{index:02d}/archive.zip",
                "oracle": f"case-{index:02d}/oracle.json",
                "files": count,
                "requested_bytes": sum(len(body) for body in expected.values()),
                "unique_blob_count": len({hashlib.sha256(body).digest() for body in expected.values()}),
                "repeated_fraction_requested": repeated_fraction,
                "drift_class": drift,
            }
        )
    manifest = {
        "schema": SCHEMA,
        "seed": seed,
        "source_commit": commit,
        "source_pool_size": len(source_pool),
        "source_selected": chosen,
        "case_count": CASE_COUNT,
        "unit": "fresh generated repository instance; shared source ecosystem and generation rules",
        "cases": cases,
    }
    (destination / "cases.json").write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return manifest


def check_bytes(result: dict[str, bytes], oracle: dict) -> dict:
    if not isinstance(result, dict) or set(result) != set(oracle["files"]):
        return {"passed": False, "reason": "source-inventory-mismatch"}
    for name, expected in oracle["files"].items():
        body = result[name]
        if not isinstance(body, bytes) or len(body) != expected["bytes"]:
            return {"passed": False, "reason": "source-size-or-type-mismatch", "path": name}
        if hashlib.sha256(body).hexdigest() != expected["sha256"]:
            return {"passed": False, "reason": "source-bytes-mismatch", "path": name}
    return {"passed": True, "files": len(result)}


def check_drift(result: dict, oracle: dict) -> dict:
    for name in ("changed", "missing", "extra"):
        if result.get(name) != oracle["drift"][name]:
            return {"passed": False, "reason": "archive-drift-mismatch", "field": name}
    return {"passed": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--seed", required=True)
    arguments = parser.parse_args()
    result = generate(arguments.source, arguments.commit, arguments.destination, arguments.seed)
    print(json.dumps({"cases": result["case_count"], "destination": str(arguments.destination)}))

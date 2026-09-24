# SPDX-License-Identifier: Apache-2.0
"""Verify source bytes and restore the complete original Git history."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

PREFIX = "AGI_Alpha_Agent_Baseline_2026-09-24/"
BUNDLE = "history/AGI_Alpha_Agent_Original_History.bundle"


def git(repo: Path, *args: str) -> str:
    """Run a checked Git command without shell interpolation."""
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def digest(data: bytes) -> str:
    """Return a SHA-256 digest."""
    return hashlib.sha256(data).hexdigest()


def verify(archive: Path) -> dict[str, Any]:
    """Check the entire archive and restore the bundle into a fresh mirror."""
    with zipfile.ZipFile(archive) as package:
        manifest = json.loads(package.read(PREFIX + "preservation/PRESERVATION_MANIFEST.json"))
        if manifest["baseline"]["baselineCommit"] != "ac9b112a44670f67d53fc3d188ef73fa16e90894":
            raise ValueError("This is not the original baseline commit")
        if (
            manifest["baseline"]["originalRefsSha256"]
            != "fd6e56b28ca79f9cbf5b4adaa54de914280910774347514fd5cc82d730a12bf4"
        ):
            raise ValueError("This is not the original branch inventory")
        source = manifest["sourceFiles"]
        expected = {PREFIX + "source/" + path for path in source}
        expected.update(PREFIX + path for path in [BUNDLE, "RESTORE.md", "VERIFY.py"])
        expected.add(PREFIX + "preservation/PRESERVATION_MANIFEST.json")
        names = package.namelist()
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("Unexpected, missing or duplicate archive entries")
        for path, record in source.items():
            name = PREFIX + "source/" + path
            data = package.read(name)
            info = package.getinfo(name)
            if len(data) != record["bytes"] or digest(data) != record["sha256"]:
                raise ValueError("Source bytes differ: " + path)
            if info.external_attr >> 16 != int(record["mode"], 8):
                raise ValueError("Source mode differs: " + path)
            oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if oid != record["gitBlob"]:
                raise ValueError("Git blob differs: " + path)
        for path, checksum in manifest["helperSha256"].items():
            if digest(package.read(PREFIX + path)) != checksum:
                raise ValueError("Helper differs: " + path)
        refs = manifest["originalRefs"]
        refs_digest = digest(json.dumps(refs, sort_keys=True, separators=(",", ":")).encode())
        if refs_digest != manifest["baseline"]["originalRefsSha256"]:
            raise ValueError("Original reference inventory differs")
        with tempfile.TemporaryDirectory(prefix="alpha-agent-restore-") as temporary:
            root = Path(temporary)
            bundle = root / "history.bundle"
            hasher = hashlib.sha256()
            with package.open(PREFIX + BUNDLE) as original, bundle.open("wb") as target:
                while block := original.read(1024 * 1024):
                    hasher.update(block)
                    target.write(block)
            if hasher.hexdigest() != manifest["historyBundle"]["sha256"]:
                raise ValueError("History bundle differs")
            if bundle.stat().st_size != manifest["historyBundle"]["bytes"]:
                raise ValueError("History bundle size differs")
            restored = root / "restored.git"
            subprocess.run(["git", "clone", "--quiet", "--mirror", str(bundle), str(restored)], check=True)
            git(restored, "bundle", "verify", str(bundle))
            git(restored, "fsck", "--full", "--strict")
            restored_refs = dict(
                line.split(" ", 1)
                for line in git(restored, "for-each-ref", "--format=%(refname) %(objectname)").splitlines()
            )
            if restored_refs != refs:
                raise ValueError("Restored branches differ")
            baseline = manifest["baseline"]
            commit = baseline["baselineCommit"]
            if git(restored, "rev-parse", "refs/heads/main") != commit:
                raise ValueError("Restored main is not the baseline")
            if git(restored, "rev-parse", commit + "^{tree}") != baseline["baselineTree"]:
                raise ValueError("Restored tree differs")
            if int(git(restored, "rev-list", "--all", "--count")) != baseline["originalCommitCount"]:
                raise ValueError("Restored commit count differs")
            tree = subprocess.check_output(["git", "-C", str(restored), "ls-tree", "-rz", commit])
            tree_records = {}
            for line in tree.split(b"\0"):
                if not line:
                    continue
                metadata, raw_path = line.split(b"\t", 1)
                path = raw_path.decode()
                mode, kind, oid = metadata.decode().split(" ")
                if kind != "blob":
                    raise ValueError("Unsupported baseline tree object")
                tree_records[path] = (mode, oid)
            if tree_records != {path: (record["mode"], record["gitBlob"]) for path, record in source.items()}:
                raise ValueError("Source inventory differs from restored Git tree")
    return {
        "verified": True,
        "sourceFiles": len(source),
        "restoredBranches": len(refs),
        "restoredCommits": baseline["originalCommitCount"],
        "baselineCommit": commit,
        "applicationRequalified": False,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 VERIFY.py /absolute/path/to/checkpoint.zip")
    print(json.dumps(verify(Path(sys.argv[1]).resolve()), indent=2))

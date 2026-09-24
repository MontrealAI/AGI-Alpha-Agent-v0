# SPDX-License-Identifier: Apache-2.0
"""Package the original baseline without rebuilding or changing its source."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from VERIFY import BUNDLE, PREFIX, digest, git, verify

HERE = Path(__file__).resolve().parent


def write_entry(package: zipfile.ZipFile, path: str, data: bytes, mode: str = "100644") -> None:
    """Write exact bytes with a fixed timestamp and original Git file mode."""
    info = zipfile.ZipInfo(PREFIX + path, (2026, 9, 24, 0, 0, 0))
    info.create_system = 3
    info.external_attr = int(mode, 8) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    package.writestr(info, data)


def file_digest(path: Path) -> str:
    """Hash a file without retaining it all in memory."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def build(repository: Path, output: Path) -> dict[str, Any]:
    """Capture all original branches and verify a complete restoration."""
    baseline = json.loads((HERE / "baseline.json").read_bytes())
    commit = baseline["baselineCommit"]
    if git(repository, "rev-parse", "refs/remotes/origin/main") != commit:
        raise ValueError("Remote main changed; review the baseline before publication")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output directory must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "AGI_Alpha_Agent_Baseline_2026-09-24.zip"
    with tempfile.TemporaryDirectory(prefix="alpha-agent-preserve-") as temporary:
        root = Path(temporary)
        snapshot = root / "original.git"
        subprocess.run(["git", "init", "--quiet", "--bare", str(snapshot)], check=True)
        git(
            snapshot,
            "fetch",
            "--quiet",
            "--no-tags",
            "--no-write-fetch-head",
            str(repository),
            "+refs/remotes/origin/*:refs/heads/*",
            "^refs/remotes/origin/HEAD",
            "^refs/remotes/origin/" + baseline["excludedPublicationBranch"],
            "+refs/tags/*:refs/tags/*",
            "^refs/tags/" + baseline["tag"],
        )
        git(snapshot, "symbolic-ref", "HEAD", "refs/heads/main")
        refs = dict(
            line.split(" ", 1)
            for line in git(snapshot, "for-each-ref", "--format=%(refname) %(objectname)").splitlines()
        )
        if len(refs) != baseline["originalRefCount"]:
            raise ValueError("Original branch count changed")
        if digest(json.dumps(refs, sort_keys=True, separators=(",", ":")).encode()) != baseline["originalRefsSha256"]:
            raise ValueError("Original branches moved; do not publish a different baseline silently")
        if git(snapshot, "rev-parse", commit + "^{tree}") != baseline["baselineTree"]:
            raise ValueError("Baseline tree changed")
        git(snapshot, "fsck", "--full", "--strict")
        bundle = root / "history.bundle"
        git(snapshot, "-c", "pack.threads=1", "bundle", "create", str(bundle), "--all")
        git(snapshot, "bundle", "verify", str(bundle))
        files: dict[str, dict[str, Any]] = {}
        entries = subprocess.check_output(["git", "-C", str(snapshot), "ls-tree", "-rz", commit]).split(b"\0")
        helpers = {name: (HERE / name).read_bytes() for name in ["RESTORE.md", "VERIFY.py"]}
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
            with subprocess.Popen(
                ["git", "-C", str(snapshot), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            ) as blobs:
                assert blobs.stdin is not None and blobs.stdout is not None
                for entry in entries:
                    if not entry:
                        continue
                    metadata, raw_path = entry.split(b"\t", 1)
                    mode, kind, oid = metadata.decode().split(" ")
                    path = raw_path.decode()
                    if kind != "blob" or mode not in {"100644", "100755"}:
                        raise ValueError("Unsupported source object: " + path)
                    blobs.stdin.write((oid + "\n").encode())
                    blobs.stdin.flush()
                    returned_oid, returned_kind, length = blobs.stdout.readline().decode().split()
                    if returned_oid != oid or returned_kind != "blob":
                        raise ValueError("Unexpected Git object")
                    data = blobs.stdout.read(int(length))
                    if len(data) != int(length) or blobs.stdout.read(1) != b"\n":
                        raise ValueError("Incomplete Git blob")
                    if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
                        raise ValueError("Unarchived Git LFS content: " + path)
                    files[path] = {"mode": mode, "gitBlob": oid, "bytes": len(data), "sha256": digest(data)}
                    write_entry(package, "source/" + path, data, mode)
                blobs.stdin.close()
                if blobs.wait() != 0:
                    raise ValueError("Git blob reader failed")
            if (
                len(files) != baseline["sourceFileCount"]
                or sum(f["bytes"] for f in files.values()) != baseline["sourceBytes"]
            ):
                raise ValueError("Original source inventory changed")
            manifest = {
                "schema": 1,
                "baseline": baseline,
                "sourceFiles": files,
                "originalRefs": refs,
                "historyBundle": {"bytes": bundle.stat().st_size, "sha256": file_digest(bundle)},
                "helperSha256": {name: digest(data) for name, data in helpers.items()},
                "validationScope": "Exact source and complete original reachable Git history; no application qualification",
            }
            manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            write_entry(package, "preservation/PRESERVATION_MANIFEST.json", manifest_bytes)
            for name, data in helpers.items():
                write_entry(package, name, data)
            info = zipfile.ZipInfo(PREFIX + BUNDLE, (2026, 9, 24, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            with package.open(info, "w") as target, bundle.open("rb") as original:
                while block := original.read(1024 * 1024):
                    target.write(block)
        (output / "PRESERVATION_MANIFEST.json").write_bytes(manifest_bytes)
        (output / "RESTORE.md").write_bytes(helpers["RESTORE.md"])
        result = verify(archive)
        assets = sorted(output.iterdir())
        (output / "SHA256SUMS.txt").write_text("".join(f"{file_digest(p)}  {p.name}\n" for p in assets))
        result.update(
            {"archive": str(archive), "archiveBytes": archive.stat().st_size, "archiveSha256": file_digest(archive)}
        )
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.repository.resolve(), args.out.resolve()), indent=2))

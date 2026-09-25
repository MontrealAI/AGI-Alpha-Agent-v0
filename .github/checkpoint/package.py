#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve the authorized in-progress commit without claiming final validation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone
import zipfile

COMMIT = "0e6e20b1839719cd930036b778ad2e2ee1d3d075"
BASELINE = "ac9b112a44670f67d53fc3d188ef73fa16e90894"
TAG = "checkpoint-2026-09-25-v1.2.1"
OUT = Path("checkpoint-assets")
OUT.mkdir(exist_ok=True)

def git(*args):
    return subprocess.check_output(["git", *args])

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

tree = git("rev-parse", COMMIT + "^{tree}").decode().strip()
assert tree == "ebc32fb89a35d77962f1577fcd842fa2984818d6"
paths = {p.decode() for p in git("ls-tree", "-r", "-z", "--name-only", COMMIT).split(b"\0") if p}
original = {p.decode() for p in git("ls-tree", "-r", "-z", "--name-only", BASELINE).split(b"\0") if p}
assert not original - paths, sorted(original - paths)
assert git("show", BASELINE + ":README.md") in git("show", COMMIT + ":README.md")
archive = OUT / (TAG + "-source.zip")
subprocess.run(["git", "archive", "--format=zip", "--prefix=AGI-Alpha-Agent-v0/",
                "--output=" + str(archive), COMMIT], check=True)
with zipfile.ZipFile(archive) as source:
    archived = {n.removeprefix("AGI-Alpha-Agent-v0/") for n in source.namelist() if not n.endswith("/")}
    assert archived == paths
    assert source.testzip() is None
git("update-ref", "refs/heads/checkpoint-snapshot", COMMIT)
bundle = OUT / (TAG + "-history.bundle")
subprocess.run(["git", "bundle", "create", str(bundle), "--all"], check=True)
subprocess.run(["git", "bundle", "verify", str(bundle)], check=True)
with tempfile.TemporaryDirectory(prefix="checkpoint-restore-") as temp:
    restored = Path(temp) / "restored"
    subprocess.run(["git", "clone", "--no-checkout", str(bundle.resolve()), str(restored)], check=True)
    got = subprocess.check_output(["git", "-C", str(restored), "rev-parse", COMMIT + "^{tree}"], text=True).strip()
    assert got == tree
    subprocess.run(["git", "-C", str(restored), "fsck", "--full"], check=True)
notes = """# $AGIALPHA Agent preservation checkpoint

This prerelease preserves current main and stable v1.2.1 before further completion work.
Source commit: 0e6e20b1839719cd930036b778ad2e2ee1d3d075
Source tree: ebc32fb89a35d77962f1577fcd842fa2984818d6

The original README and flywheel remain verbatim; all original tracked paths are retained.
Assets include exact source, self-contained Git history, recovery instructions, manifest,
and SHA-256 checksums. A fresh bundle clone, target-tree comparison and git fsck are
required before publication. All uploaded bytes are downloaded and verified before
the draft becomes public. Existing tags and releases remain unchanged.

Stable release: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/v1.2.1
Validation: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/36118732252

The stable release passed its runtime, real-model, browser/contracts, minimal/full
gallery, quality, regression, packaging and historical-main-CI gates.
Regression: 1061 passed, 55 skipped, 5 expected failures, 82.09% coverage.
See v1.2.1 VALIDATION.md and CAPABILITIES.md for tested scope and remaining boundaries.
This checkpoint makes no claim of general AGI, guaranteed returns or perfect completion.
Operator databases, private credentials and wallets require separate runtime backups.
"""

(OUT / "CHECKPOINT_NOTES.md").write_text(notes, encoding="utf-8")
restore = f"""# Restore this checkpoint

Download every asset into one directory. On Linux, verify all bytes first:

    sha256sum -c SHA256SUMS

For a source-only copy:

    unzip {archive.name}

For source plus preserved Git history, with no GitHub access required:

    git clone {bundle.name} recovered-alpha-agent
    git -C recovered-alpha-agent checkout --detach {COMMIT}
    git -C recovered-alpha-agent rev-parse HEAD
    git -C recovered-alpha-agent fsck --full

The commit must be {COMMIT}; its tree must be {tree}.
Use a new directory so restoration does not overwrite an existing working copy.
Read CHECKPOINT_NOTES.md before running this checkpoint.
For the tested stable release, use v1.2.1 and its OPERATIONS.md installation guide.
The snapshot contains repository source/history, not operator-private wallets,
credentials, database volumes, or external services. Runtime data must be backed up
separately using the documented alpha-agent backup procedure.
"""
(OUT / "RESTORE.md").write_text(restore, encoding="utf-8")
manifest = {
    "schema_version": 1, "kind": "development-checkpoint", "tag": TAG, "commit": COMMIT,
    "tree": tree, "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "workflow_commit": os.environ["GITHUB_SHA"],
    "workflow_run": os.environ["GITHUB_SERVER_URL"] + "/" + os.environ["GITHUB_REPOSITORY"]
                    + "/actions/runs/" + os.environ["GITHUB_RUN_ID"],
    "original_files_preserved": len(original), "original_readme_verbatim": True,
    "source_archive_verified": True, "bundle_restored_and_fsck_verified": True,
    "final_release_validation": "v1.2.1 validated; see CHECKPOINT_NOTES.md",
    "assets": [{"name": p.name, "size": p.stat().st_size, "sha256": digest(p)}
               for p in sorted(OUT.iterdir())]
}
(OUT / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(OUT / "SHA256SUMS").write_text(
    "".join(f"{digest(p)}  {p.name}\n" for p in sorted(OUT.iterdir())), encoding="utf-8")
print(json.dumps(manifest, indent=2))

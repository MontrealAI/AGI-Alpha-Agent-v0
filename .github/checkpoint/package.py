#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preserve the authorized in-progress commit without claiming final validation."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone
import zipfile

COMMIT = "198621c8bf59063e3afc2310bb24cd6c4aac8971"
BASELINE = "ac9b112a44670f67d53fc3d188ef73fa16e90894"
TAG = "checkpoint-2026-09-25-v1.3.0-wip"
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
assert tree == "80c357c23c027c3b505f3359920232c3f7632e10"
paths = {p.decode() for p in git("ls-tree", "-r", "-z", "--name-only", COMMIT).split(b"\0") if p}
original = {p.decode() for p in git("ls-tree", "-r", "-z", "--name-only", BASELINE).split(b"\0") if p}
assert not original - paths, sorted(original - paths)
def normalize_badges(value):
    return re.sub(rb"(https://github.com/montrealai/AGI-Alpha-Agent-v0/actions/workflows/(?:pr-ci|ci|smoke|ci-health)\.yml(?:/badge\.svg)?)(?:\?[^)\s]*)?", rb"\1", value)
assert normalize_badges(git("show", BASELINE + ":README.md")) in normalize_badges(git("show", COMMIT + ":README.md"))
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
notes = "# $AGIALPHA Agent v1.3.0 work-in-progress checkpoint\n\nPublished at the owner's request to preserve today's work before resuming tomorrow.\nExact source commit: 198621c8bf59063e3afc2310bb24cd6c4aac8971\nExact source tree: 80c357c23c027c3b505f3359920232c3f7632e10\nPull request: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/pull/4715\n\nThis is a preservation prerelease, not the completed stable v1.3.0 release.\nStable v1.2.1 and every earlier release remain unchanged. Main is not merged.\nAll 2,125 original paths and the historical README/flywheels are preserved.\nOnly the historical CI badge URL queries changed to explicitly track main.\n\nCompleted work includes real pinned browser ONNX inference and offline caching,\nmemory-only browser credentials, bounded evolutionary populations, strict-CSP WebGL,\nworking AIGA startup, owner-only Windows permissions, reliable SQLite backup cleanup,\nautomatic nine-platform/Python smoke coverage, updated version/badges, and packaging\nof a ready-to-serve browser distribution with model hash verification.\n\nValidation recorded before checkpoint publication:\n- 72 runtime tests and 18 publication/preservation/download tests passed locally.\n- All local repository hooks passed with Node 22.17.1; strict runtime types passed.\n- All nine OS/Python smoke combinations passed on this exact commit:\n  https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/36135375710\n- PR CI passed:\n  https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/36135381361\n- Candidate runtime builds, Docker, real local inference, browser/contracts,\n  full/minimal galleries and hosted quality passed:\n  https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/36135375714\n- Full Python regression was still running when this checkpoint was prepared;\n  candidate packaging and stable publication were not yet complete.\n  Consult that run for later results; pending work is not reported as passed.\n- Browser checks: 9 passing; Solidity: 36 passing; real local EVM lifecycle passed.\n  Actual local Qwen inference verified six quotes; actual ONNX inference was\n  repeated after an offline reload. Cloud-provider response checks use fixtures.\n\nAssets include exact source, a self-contained Git history bundle, recovery and resume\ninstructions, a timestamped validation snapshot, a manifest and SHA-256 checksums.\nPublication requires a fresh bundle clone, matching source tree, git fsck and\nredownloading every uploaded byte to verify its hash.\n\nThis checkpoint does not claim general AGI/ASI, perfect completion, guaranteed\nreturns, an independent security audit, mainnet deployment or automatic treasury spending.\nOperator-private state, credentials and wallets need separate runtime backups.\nStable release: https://github.com/MontrealAI/AGI-Alpha-Agent-v0/releases/tag/v1.2.1\n"

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
(OUT / "RESUME.md").write_text("# Resume tomorrow\n\n1. Restore this exact checkpoint using RESTORE.md, or fetch branch fix/agent-integration-completion.\n2. Confirm HEAD is 198621c8bf59063e3afc2310bb24cd6c4aac8971; PR 4715 must remain open until acceptance is complete.\n3. Inspect candidate acceptance run 36135375714. Regression was running when work paused.\n   If it failed, fix the cause and rerun the complete required acceptance on the new commit.\n4. Require successful regression/coverage, types, quality, browser/contracts, real model,\n   full/minimal galleries, three runtime builds and clean package installation.\n   Smoke run 36135375710 passed all nine OS/Python combinations; PR CI 36135381361 passed.\n5. Inspect the candidate package and update PR validation evidence. Merge PR 4715 only\n   after its exact head passes. Use a normal merge; preserve all original files and flywheels.\n6. Let the main-commit release workflow rerun and require historical Integration CI, PR CI\n   and Smoke Test on the exact merged commit. It publishes stable v1.3.0 only after success.\n7. Verify the annotated v1.3.0 tag, public release assets/checksums, manifest/evidence,\n   latest stable release and live badge states. Never move earlier tags or replace public assets.\n\nThe user asked to stop implementation after preserving this checkpoint. No main merge\nor stable v1.3.0 publication was performed as part of this pause.\nAll source changes are committed. Local generated model downloads and worker build outputs\nare reproducible and are not additional uncommitted product changes.\nThe full browser binary was retained by candidate CI as browser-distribution, artifact\n10865105595 (554343031 bytes including the artifact wrapper); regenerate from the pinned\nmanifest if CI retention expires. Do not depend on temporary workspace files.\n", encoding="utf-8")
(OUT / "validation-status.json").write_text("{\n  \"source_commit\": \"198621c8bf59063e3afc2310bb24cd6c4aac8971\",\n  \"candidate_run\": \"https://github.com/MontrealAI/AGI-Alpha-Agent-v0/actions/runs/36135375714\",\n  \"status_scope\": \"Snapshot at checkpoint preparation; consult run for later results\",\n  \"jobs\": [\n    {\n      \"name\": \"regression\",\n      \"id\": 108072236579,\n      \"status\": \"in_progress\",\n      \"conclusion\": null\n    },\n    {\n      \"name\": \"browser-contracts\",\n      \"id\": 108072236910,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    },\n    {\n      \"name\": \"historical-ci\",\n      \"id\": 108072236926,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    },\n    {\n      \"name\": \"runtime (3.12)\",\n      \"id\": 108072236969,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    },\n    {\n      \"name\": \"gallery (full)\",\n      \"id\": 108072237062,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    },\n    {\n      \"name\": \"gallery (minimal)\",\n      \"id\": 108072237077,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    },\n    {\n      \"name\": \"runtime (3.11)\",\n      \"id\": 108072237155,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    },\n    {\n      \"name\": \"runtime (3.13)\",\n      \"id\": 108072237166,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    },\n    {\n      \"name\": \"quality\",\n      \"id\": 108072237268,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    },\n    {\n      \"name\": \"real-model\",\n      \"id\": 108072237312,\n      \"status\": \"completed\",\n      \"conclusion\": \"success\"\n    }\n  ],\n  \"smoke\": {\n    \"run\": 36135375710,\n    \"result\": \"success\",\n    \"combinations\": 9\n  },\n  \"pr_ci\": {\n    \"run\": 36135381361,\n    \"result\": \"success\"\n  },\n  \"local\": {\n    \"runtime_passed\": 72,\n    \"publication_preservation_download_passed\": 18,\n    \"all_hooks\": \"passed\",\n    \"strict_runtime_types\": \"passed\"\n  },\n  \"next\": \"Full regression, candidate packaging, main merge and main-commit stable release acceptance\"\n}\n", encoding="utf-8")
manifest = {
    "schema_version": 1, "kind": "development-checkpoint", "tag": TAG, "commit": COMMIT,
    "tree": tree, "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "workflow_commit": os.environ["GITHUB_SHA"],
    "workflow_run": os.environ["GITHUB_SERVER_URL"] + "/" + os.environ["GITHUB_REPOSITORY"]
                    + "/actions/runs/" + os.environ["GITHUB_RUN_ID"],
    "original_files_preserved": len(original), "original_readme_text_and_flywheels_preserved": True, "permitted_readme_changes": "CI badge URL queries only",
    "source_archive_verified": True, "bundle_restored_and_fsck_verified": True,
    "final_release_validation": "v1.3.0 work in progress; full regression pending at preparation; see validation-status.json",
    "assets": [{"name": p.name, "size": p.stat().st_size, "sha256": digest(p)}
               for p in sorted(OUT.iterdir())]
}
(OUT / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(OUT / "SHA256SUMS").write_text(
    "".join(f"{digest(p)}  {p.name}\n" for p in sorted(OUT.iterdir())), encoding="utf-8")
print(json.dumps(manifest, indent=2))

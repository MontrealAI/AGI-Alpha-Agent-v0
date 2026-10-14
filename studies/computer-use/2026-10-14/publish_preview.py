# SPDX-License-Identifier: Apache-2.0
"""Publish a separate immutable study preview after exact-head PR and study checks."""

from __future__ import annotations
import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

REPO = "MontrealAI/AGI-Alpha-Agent-v0"
TAG = "study-computer-use-2026-10-14-r1"


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True)


def api(path: str):
    return json.loads(gh("api", f"repos/{REPO}/" + path))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    head = os.environ["STUDY_HEAD"]
    number = int(os.environ["STUDY_PR"])
    if os.environ.get("GITHUB_REPOSITORY") != REPO or os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        raise RuntimeError("Only the authorized same-repository study PR may publish")
    pr = api(f"pulls/{number}")
    if (
        pr["head"]["sha"] != head
        or pr["head"]["repo"]["full_name"] != REPO
        or pr["head"]["ref"] != "docs/try-work-evidence-pilot-20261014"
    ):
        raise RuntimeError("Study source moved or has an unexpected origin")
    required = {"pr-ci.yml", "smoke.yml"}
    for attempt in range(40):
        runs = api(f"actions/runs?head_sha={head}&event=pull_request&per_page=100")["workflow_runs"]
        latest = {}
        for run in sorted(runs, key=lambda r: (r["created_at"], r.get("run_attempt", 1))):
            name = run["path"].split("/")[-1]
            if name in required:
                latest[name] = run
        if set(latest) == required and all(r["conclusion"] == "success" for r in latest.values()):
            break
        if any(r["status"] == "completed" and r["conclusion"] not in ["success", "cancelled"] for r in latest.values()):
            raise RuntimeError("A required exact-head PR check failed")
        if attempt == 39:
            raise RuntimeError("Required PR checks are not complete; no public study release was made")
        time.sleep(30)
    if api(f"pulls/{number}")["head"]["sha"] != head:
        raise RuntimeError("PR head moved before publication")
    dist = Path(os.environ["STUDY_DIST"])
    for name in ["work-evidence-kit.zip", "fresh-evidence.zip", "SHA256SUMS"]:
        if not (dist / name).is_file():
            raise RuntimeError("Missing publication asset: " + name)
    prior = subprocess.run(["gh", "api", f"repos/{REPO}/releases/tags/{TAG}"], text=True, capture_output=True)
    if prior.returncode:
        notes = Path(os.environ["RUNNER_TEMP"]) / "study-release-notes.md"
        notes.write_text(
            "# Try the work — Evidence & Recovery Kit\n\nDownload work-evidence-kit.zip, extract it and open START_HERE.html. The kit contains actual synthetic study applications, exact source files, the public report, recovery guidance, reproducibility tools and a prospective human pilot.\n\nFresh checks and screenshots are in fresh-evidence.zip. Both ZIPs have SHA-256 checksums.\n\nThis is a separate study preview, not an AGI Alpha software release or production deployment. Zero humans were observed. Fewer scripted controls are not measured human time savings. The kit is not the original 98-file Office/PDF archive. No model API was called and the repository runtime was not exercised by these study tests.\n\nExact source commit: `"
            + head
            + "`.\n"
        )
        gh(
            "release",
            "create",
            TAG,
            "--repo",
            REPO,
            "--target",
            head,
            "--draft",
            "--prerelease",
            "--latest=false",
            "--title",
            "Try the Work — reproducible study kit (preview)",
            "--notes-file",
            str(notes),
        )
        release = api(f"releases/tags/{TAG}")
    else:
        release = json.loads(prior.stdout)
    ref = api(f"git/ref/tags/{TAG}")["object"]
    if ref["type"] == "tag":
        ref = api("git/tags/" + ref["sha"])["object"]
    if ref["type"] != "commit" or ref["sha"] != head:
        raise RuntimeError("Frozen tag differs; use a new study revision instead")
    assets = sorted(p for p in dist.iterdir() if p.is_file())
    if release["draft"]:
        for path in assets:
            gh("release", "upload", TAG, str(path), "--repo", REPO, "--clobber")
    with tempfile.TemporaryDirectory() as temp:
        gh("release", "download", TAG, "--repo", REPO, "--dir", temp)
        for path in assets:
            other = Path(temp) / path.name
            if not other.is_file() or digest(other) != digest(path):
                raise RuntimeError("Uploaded asset mismatch: " + path.name)
    if api(f"pulls/{number}")["head"]["sha"] != head:
        raise RuntimeError("Source moved; release stays draft")
    if release["draft"]:
        gh(
            "api",
            "--method",
            "PATCH",
            f"repos/{REPO}/releases/{release['id']}",
            "-F",
            "draft=false",
            "-F",
            "prerelease=true",
            "-f",
            "make_latest=false",
        )
    public = api(f"releases/tags/{TAG}")
    if public["draft"]:
        raise RuntimeError("Publication remained a draft")
    print(public["html_url"])


if __name__ == "__main__":
    main()

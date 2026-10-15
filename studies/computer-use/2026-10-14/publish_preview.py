# SPDX-License-Identifier: Apache-2.0
"""Publish a separate immutable study preview after exact-head PR and study checks."""

from __future__ import annotations
import hashlib
import json
import os
import subprocess
import tempfile
import time
import re
import zipfile
from verify_and_replay import safe_file, verify_sources, verify_results
from pathlib import Path

REPO = "MontrealAI/AGI-Alpha-Agent-v0"
TAG = "study-computer-use-2026-10-14-r1"


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True)


def api(path: str):
    return json.loads(gh("api", f"repos/{REPO}/" + path))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


ASSETS = {
    "work-evidence-kit.zip",
    "fresh-evidence.zip",
    "complete-study-kit.zip",
    "REPORT.pdf",
    "PILOT_PROTOCOL.pdf",
    "SHA256SUMS",
}


def zip_files(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        files = {}
        if sum(x.file_size for x in archive.infolist()) > 50_000_000:
            raise ValueError("Study archive exceeds the reviewed size limit")
        for info in archive.infolist():
            name = info.filename
            if info.is_dir():
                continue
            if (
                name.startswith("/")
                or "\\" in name
                or ":" in name
                or any(x in {"", ".", ".."} for x in name.split("/"))
                or name in files
                or (info.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Unsafe or duplicate archive member")
            files[name] = archive.read(info)
        return files


def check_sums(files: dict[str, bytes], manifest: str) -> None:
    rows = {}
    for line in files[manifest].decode("utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  (.+)", line)
        if not match or match[2] in rows or match[2] == manifest:
            raise ValueError("Invalid distribution checksum manifest")
        rows[match[2]] = match[1]
    if set(rows) != set(files) - {manifest}:
        raise ValueError("Distribution checksum membership differs")
    for name, expected in rows.items():
        if hashlib.sha256(files[name]).hexdigest() != expected:
            raise ValueError("Distribution checksum mismatch: " + name)


def validate_distribution(dist: Path, head: str) -> None:
    """Validate before uploading, without a GitHub write or a model/provider call."""
    if not re.fullmatch(r"[a-f0-9]{40}", head):
        raise ValueError("Invalid source commit")
    if {p.name for p in dist.iterdir()} != ASSETS:
        raise ValueError("Distribution assets differ from the six reviewed files")
    files = {name: safe_file(dist, name).read_bytes() for name in ASSETS}
    check_sums(files, "SHA256SUMS")
    for name in ["REPORT.pdf", "PILOT_PROTOCOL.pdf"]:
        if not files[name].startswith(b"%PDF-"):
            raise ValueError("Invalid PDF asset")
    source = zip_files(dist / "work-evidence-kit.zip")
    evidence = zip_files(dist / "fresh-evidence.zip")
    check_sums(source, "SHA256SUMS")
    root = Path(__file__).resolve().parent
    verify_sources(root)
    for name, content in source.items():
        if safe_file(root, name).read_bytes() != content:
            raise ValueError("Source asset differs from checked-out source: " + name)
    if evidence["publication/SOURCE_COMMIT.txt"].decode().strip() != head:
        raise ValueError("Publication evidence refers to a different source commit")
    environment = json.loads(evidence["publication/ENVIRONMENT.json"])
    if environment["testedCommit"] != head or environment["humanParticipants"] != 0:
        raise ValueError("Publication environment binding differs")
    publication = json.loads(evidence["publication/PUBLICATION_CHECKS.json"])
    if (
        publication["mode"] != "HTTP-and-file"
        or not publication["httpDownloadsAndRecovery"]
        or not publication["localFileOpening"]
        or len(publication["combinations"]) != 16
        or not all(x["passed"] is True for x in publication["combinations"])
        or {(x["width"], x["french"], x["large"]) for x in publication["combinations"]}
        != {(w, f, large) for w in [320, 390, 900, 1440] for f in [False, True] for large in [False, True]}
        or publication.get("keyboardAndReadingPreferences") is not True
    ):
        raise ValueError("Required browser publication evidence is incomplete")
    negative = json.loads(evidence["replay/VERIFIER_CHECKS.json"])
    from check_negative_controls import CASES

    if (
        (negative["passed"], negative["total"]) != (len(CASES), len(CASES))
        or [x["case"] for x in negative["checks"]] != list(CASES)
        or not all(x["refused"] is True for x in negative["checks"])
    ):
        raise ValueError("Verifier negative-control evidence is incomplete")
    with tempfile.TemporaryDirectory(prefix="study-dist-check-") as temp:
        target = Path(temp)
        for name, content in source.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        for name, content in evidence.items():
            if name.startswith("replay/"):
                path = target / "03_Evidence" / name.removeprefix("replay/")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        if verify_results(target) != json.loads(evidence["FRESH_RESULTS.json"]):
            raise ValueError("Fresh results differ from the raw replay records")
    combined = zip_files(dist / "complete-study-kit.zip")
    check_sums(combined, "PUBLICATION_SHA256SUMS")
    expected = dict(source)
    expected.update({"FRESH_EVIDENCE/" + name: data for name, data in evidence.items()})
    expected.update({name: files[name] for name in ["REPORT.pdf", "PILOT_PROTOCOL.pdf"]})
    if set(combined) != set(expected) | {"READ_FIRST.txt", "PUBLICATION_SHA256SUMS"}:
        raise ValueError("Complete kit membership differs")
    if any(combined[name] != data for name, data in expected.items()):
        raise ValueError("Complete kit differs from its component assets")


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
    validate_distribution(dist, head)
    prior = subprocess.run(["gh", "api", f"repos/{REPO}/releases/tags/{TAG}"], text=True, capture_output=True)
    if prior.returncode:
        notes = Path(os.environ["RUNNER_TEMP"]) / "study-release-notes.md"
        notes.write_text(
            (
                "# Try the work — Evidence & Recovery Kit\n\nDownload work-evidence-"
                "kit.zip, extract it and open START_HERE.html. The kit contains ac"
                "tual synthetic study applications, exact source files, the public"
                " report, recovery guidance, reproducibility tools and a prospecti"
                "ve human pilot.\n\nFresh checks and screenshots are in fresh-eviden"
                "ce.zip. Both ZIPs have SHA-256 checksums.\n\nThis is a separate stu"
                "dy preview, not an AGI Alpha software release or production deplo"
                "yment. Zero humans were observed. Fewer scripted controls are not"
                " measured human time savings. The kit is not the original 98-file"
                " Office/PDF archive. No model API was called and the repository r"
                "untime was not exercised by these study tests.\n\nExact source comm"
                "it: `"
            )
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
    if {asset["name"] for asset in api(f"releases/tags/{TAG}")["assets"]} != ASSETS:
        raise RuntimeError("Uploaded release contains unexpected or missing assets")
    with tempfile.TemporaryDirectory() as temp:
        gh("release", "download", TAG, "--repo", REPO, "--dir", temp)
        validate_distribution(Path(temp), head)
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

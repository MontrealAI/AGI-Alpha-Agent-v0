# SPDX-License-Identifier: Apache-2.0
"""Verify and publish the existing checkpoint draft without replacing assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from VERIFY import PREFIX, verify

REPO = "MontrealAI/AGI-Alpha-Agent-v0"
RELEASE_ID = 395917333
TAG = "baseline-2026-09-24"
BASELINE = "ac9b112a44670f67d53fc3d188ef73fa16e90894"
ASSETS = {
    "AGI_Alpha_Agent_Baseline_2026-09-24.zip",
    "PRESERVATION_MANIFEST.json",
    "RESTORE.md",
    "SHA256SUMS.txt",
}


def api(path: str, *args: str) -> dict[str, Any]:
    """Read a GitHub object or perform the explicit final publication."""
    value = json.loads(subprocess.check_output(["gh", "api", f"repos/{REPO}/{path}", *args], text=True))
    if not isinstance(value, dict):
        raise TypeError("Expected a GitHub object")
    return value


def main(output: Path) -> None:
    """Download, restore and validate every existing asset before publishing."""
    release = api(f"releases/{RELEASE_ID}")
    if not release["draft"] or not release["prerelease"] or release["tag_name"] != TAG:
        raise ValueError("Refusing to change an unexpected or already published release")
    if api("git/ref/heads/main")["object"]["sha"] != BASELINE:
        raise ValueError("Original main changed")
    tag = api(f"git/ref/tags/{TAG}")["object"]
    if tag["type"] == "tag":
        tag = api("git/tags/" + tag["sha"])["object"]
    if tag["type"] != "commit" or tag["sha"] != BASELINE:
        raise ValueError("Checkpoint tag does not point to the original baseline")
    if {asset["name"] for asset in release["assets"]} != ASSETS or len(release["assets"]) != len(ASSETS):
        raise ValueError("Unexpected release assets")
    output.mkdir(parents=True, exist_ok=False)
    for asset in release["assets"]:
        path = output / asset["name"]
        with path.open("wb") as handle:
            subprocess.run(
                ["gh", "api", f"repos/{REPO}/releases/assets/{asset['id']}", "-H", "Accept: application/octet-stream"],
                stdout=handle,
                check=True,
            )
        with path.open("rb") as handle:
            checksum = hashlib.file_digest(handle, "sha256").hexdigest()
        if path.stat().st_size != asset["size"] or asset["digest"] != "sha256:" + checksum:
            raise ValueError("Uploaded asset bytes differ: " + path.name)
    checksums = {}
    for line in (output / "SHA256SUMS.txt").read_text().splitlines():
        checksum, name = line.split("  ", 1)
        checksums[name] = checksum
    if set(checksums) != ASSETS - {"SHA256SUMS.txt"}:
        raise ValueError("Checksum inventory differs")
    for name, expected in checksums.items():
        with (output / name).open("rb") as handle:
            if hashlib.file_digest(handle, "sha256").hexdigest() != expected:
                raise ValueError("Published checksum differs: " + name)
    archive = output / "AGI_Alpha_Agent_Baseline_2026-09-24.zip"
    with zipfile.ZipFile(archive) as package:
        if (
            package.read(PREFIX + "preservation/PRESERVATION_MANIFEST.json")
            != (output / "PRESERVATION_MANIFEST.json").read_bytes()
        ):
            raise ValueError("Companion manifest differs from the archive")
        if package.read(PREFIX + "RESTORE.md") != (output / "RESTORE.md").read_bytes():
            raise ValueError("Companion recovery guide differs from the archive")
    print(json.dumps(verify(archive)), flush=True)
    if api("git/ref/heads/main")["object"]["sha"] != BASELINE:
        raise ValueError("Original main changed before publication")
    published = api(
        f"releases/{RELEASE_ID}",
        "--method",
        "PATCH",
        "-F",
        "draft=false",
        "-F",
        "prerelease=true",
        "-f",
        "make_latest=false",
    )
    if published["draft"] or not published["prerelease"] or published["tag_name"] != TAG:
        raise ValueError("Publication status did not match the checkpoint")
    print(json.dumps({"published": published["html_url"], "releaseId": RELEASE_ID}), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: resume_draft.py /absolute/new/download-directory")
    main(Path(sys.argv[1]).resolve())

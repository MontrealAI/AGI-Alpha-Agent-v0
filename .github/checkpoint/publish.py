#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Publish a verified release from authorized main-branch GitHub Actions only."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile



def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True)


def main() -> None:
    repo = "MontrealAI/AGI-Alpha-Agent-v0"
    if os.getenv("GITHUB_REPOSITORY") != repo or os.getenv("GITHUB_REF") != "refs/heads/release/checkpoint-2026-09-25-v1.2.1":
        raise RuntimeError("publication is restricted to the authorized checkpoint branch")
    sha = "0e6e20b1839719cd930036b778ad2e2ee1d3d075"
    folder = Path("checkpoint-assets")
    manifest = json.loads((folder / "release-manifest.json").read_bytes())
    if manifest["commit"] != sha:
        raise ValueError("package commit differs from tested commit")
    tag = "checkpoint-2026-09-25-v1.2.1"
    # Never move or overwrite an existing tag or published release.
    releases = json.loads(gh("api", f"repos/{repo}/releases?per_page=100"))
    prior = next((item for item in releases if item["tag_name"] == tag), None)
    if prior and not prior["draft"]:
        print(f"{tag} is already public; its tag and assets remain unchanged: {prior['html_url']}")
        return
    ref = subprocess.run(["gh", "api", f"repos/{repo}/git/ref/tags/{tag}"], capture_output=True, text=True)
    if ref.returncode == 0:
        obj = json.loads(ref.stdout)["object"]
        target = (
            json.loads(gh("api", f"repos/{repo}/git/tags/{obj['sha']}"))["object"]["sha"]
            if obj["type"] == "tag"
            else obj["sha"]
        )
        if target != sha:
            raise ValueError("existing tag points to a different commit")
    else:
        annotated = json.loads(
            gh(
                "api",
                "--method",
                "POST",
                f"repos/{repo}/git/tags",
                "-f",
                f"tag={tag}",
                "-f",
                "message=$AGIALPHA Agent development checkpoint: exact current source and Git history; stable v1.2.1 preserved before further completion",
                "-f",
                f"object={sha}",
                "-f",
                "type=commit",
            )
        )
        gh(
            "api",
            "--method",
            "POST",
            f"repos/{repo}/git/refs",
            "-f",
            f"ref=refs/tags/{tag}",
            "-f",
            f"sha={annotated['sha']}",
        )
    if not prior:
        gh(
            "release",
            "create",
            tag,
            "--repo",
            repo,
            "--verify-tag",
            "--draft",
            "--prerelease",
            "--title",
            "$AGIALPHA Agent checkpoint 2026-09-25",
            "--notes-file",
            str(folder / "CHECKPOINT_NOTES.md"),
        )
    # Upload is idempotent only while the release remains a draft.
    for path in sorted(folder.iterdir()):
        gh("release", "upload", tag, str(path), "--repo", repo, "--clobber")
    releases = json.loads(gh("api", f"repos/{repo}/releases?per_page=100"))
    draft = next(item for item in releases if item["tag_name"] == tag)
    if not draft["draft"] or {item["name"] for item in draft["assets"]} != {p.name for p in folder.iterdir()}:
        raise ValueError("draft assets differ from package")
    # Re-download every uploaded byte before changing visibility.
    with tempfile.TemporaryDirectory(prefix="alpha-release-verify-") as temp:
        gh("release", "download", tag, "--repo", repo, "--dir", temp)
        for path in folder.iterdir():
            if (
                hashlib.sha256(path.read_bytes()).digest()
                != hashlib.sha256((Path(temp) / path.name).read_bytes()).digest()
            ):
                raise ValueError(f"uploaded asset checksum mismatch: {path.name}")
    gh(
        "api",
        "--method",
        "PATCH",
        f"repos/{repo}/releases/{draft['id']}",
        "-F",
        "draft=false",
        "-F",
        "prerelease=true",
        "-f",
        "make_latest=false",
    )
    public = json.loads(gh("api", f"repos/{repo}/releases/tags/{tag}"))
    assert not public["draft"] and public["prerelease"]
    print(public["html_url"])


if __name__ == "__main__":
    main()

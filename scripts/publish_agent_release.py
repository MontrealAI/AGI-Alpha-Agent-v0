#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Publish a verified release from authorized main-branch GitHub Actions only."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import tomllib
from pathlib import Path

from alpha_factory_v1.utils.disclaimer import DISCLAIMER
from scripts.release_context import require_current_main
from scripts.release_packs import digest, require_asset_limits


def gh(*args: str) -> str:
    return subprocess.check_output(["gh", *args], text=True)


def tag_commit(repo: str, obj: dict[str, str]) -> str:
    """Require a lightweight commit tag or a one-level annotated commit tag."""
    if obj["type"] == "tag":
        obj = json.loads(gh("api", f"repos/{repo}/git/tags/{obj['sha']}"))["object"]
    if obj["type"] != "commit":
        raise ValueError("existing tag does not point directly to a commit")
    return obj["sha"]


def preflight() -> None:
    """Fail early on a reused version without packaging, activation or mutations."""
    sha = require_current_main()
    repo = "MontrealAI/AGI-Alpha-Agent-v0"
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("declared release version must be a three-part numeric version")
    tag = f"v{version}"
    # matching-refs returns an empty list for an unused tag, while authorization
    # and service errors still fail closed. Never treat an arbitrary API error
    # as permission to create a tag. Filter exact names because this is a prefix API.
    refs = json.loads(gh("api", f"repos/{repo}/git/matching-refs/tags/{tag}"))
    if not isinstance(refs, list):
        raise ValueError("invalid tag lookup response")
    exact = [ref for ref in refs if ref["ref"] == f"refs/tags/{tag}"]
    if len(exact) > 1:
        raise ValueError("ambiguous existing release tag")
    if exact and tag_commit(repo, exact[0]["object"]) != sha:
        raise ValueError(
            f"{tag} already identifies another commit; increment the release version before running acceptance. "
            "Existing release tags and assets must remain unchanged."
        )
    print(f"Publication preflight passed for {tag} at {sha}; full acceptance is still required")


def main() -> None:
    repo = "MontrealAI/AGI-Alpha-Agent-v0"
    if os.getenv("GITHUB_REPOSITORY") != repo or os.getenv("GITHUB_REF") != "refs/heads/main":
        raise RuntimeError("publication is restricted to the authorized repository main branch")
    sha = os.environ["GITHUB_SHA"]
    folder = Path("release")
    manifest = json.loads((folder / "release-manifest.json").read_bytes())
    if manifest["commit"] != sha:
        raise ValueError("package commit differs from tested commit")
    version = manifest["version"]
    declared = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version) or version != declared:
        raise ValueError("package version differs from the declared release version")
    tag = f"v{version}"
    # Never move or overwrite an existing tag or published release.
    releases = json.loads(gh("api", f"repos/{repo}/releases?per_page=100"))
    prior = next((item for item in releases if item["tag_name"] == tag), None)
    if prior and not prior["draft"]:
        obj = json.loads(gh("api", f"repos/{repo}/git/ref/tags/{tag}"))["object"]
        if tag_commit(repo, obj) != sha:
            raise ValueError("existing public tag points to a different commit; increment the release version")
        print(f"{tag} is already public; its tag and assets remain unchanged: {prior['html_url']}")
        return
    require_asset_limits(folder)
    require_current_main()
    ref = subprocess.run(["gh", "api", f"repos/{repo}/git/ref/tags/{tag}"], capture_output=True, text=True, check=False)
    if ref.returncode == 0:
        obj = json.loads(ref.stdout)["object"]
        target = tag_commit(repo, obj)
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
                f"message=$AGIALPHA Agent {version}: tested bounded runtime; preservation verified",
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
            "--title",
            f"$AGIALPHA Agent {version}",
            "--notes-file",
            str(folder / f"RELEASE_NOTES_{version}.md"),
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
            downloaded = Path(temp) / path.name
            if (
                downloaded.is_symlink()
                or downloaded.stat().st_size != path.stat().st_size
                or digest(path) != digest(downloaded)
            ):
                raise ValueError(f"uploaded asset checksum mismatch: {path.name}")
    # Upload and re-download can take minutes; recheck immediately before visibility.
    require_current_main()
    gh(
        "api",
        "--method",
        "PATCH",
        f"repos/{repo}/releases/{draft['id']}",
        "-F",
        "draft=false",
        "-F",
        "prerelease=false",
        "-f",
        "make_latest=true",
    )
    public = json.loads(gh("api", f"repos/{repo}/releases/tags/{tag}"))
    assert not public["draft"] and not public["prerelease"]
    print(public["html_url"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="Read-only current-main and version-collision check")
    args = parser.parse_args()
    if args.preflight:
        preflight()
    else:
        main()

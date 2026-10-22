# SPDX-License-Identifier: Apache-2.0
"""Reject superseded main runs before deployment or release publication."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"


def require_paper_descendant(root: Path, software_sha: str, main_sha: str) -> None:
    """Admit only a complete, independently reproduced paper history above S."""
    from scripts.paper_changes import prove_paper_descendants

    # Checkout may predate a paper push. Fetch public source objects only, never
    # replace the software checkout or execute the descendant's scripts.
    available = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(root), "cat-file", "-e", main_sha + "^{commit}"],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if available.returncode:
        subprocess.run(
            [
                "git",
                "--no-replace-objects",
                "-C",
                str(root),
                "fetch",
                "--no-tags",
                f"https://github.com/{REPOSITORY}.git",
                main_sha,
            ],
            check=True,
            timeout=120,
        )
    proof = prove_paper_descendants(root, software_sha, main_sha)
    if proof.get("mode") != "paper":
        raise ValueError("A strict paper-only descendant proof is required")


def require_unpublished_software() -> None:
    """An already public software rerun must not overwrite a later paper site."""
    import tomllib

    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid software version")
    result = subprocess.run(
        ["gh", "api", f"repos/{REPOSITORY}/releases/tags/v{version}", "-H", "Cache-Control: no-cache"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        if "(HTTP 404)" in result.stderr:
            return
        raise RuntimeError("Cannot establish whether software is already public")
    release = json.loads(result.stdout)
    if (
        not isinstance(release, dict)
        or release.get("tag_name") != f"v{version}"
        or type(release.get("draft")) is not bool
    ):
        raise ValueError("Invalid exact release lookup")
    if release["draft"] is False:
        raise RuntimeError("Software is already public; do not redeploy its older base over the paper site")


def require_current_main() -> str:
    """Check the authorized context and current remote main, failing closed."""
    sha = os.environ.get("GITHUB_SHA", "")
    if (
        os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or not re.fullmatch(r"[0-9a-f]{40}", sha)
    ):
        raise ValueError("Publication requires the authorized repository's main commit")
    raw = subprocess.check_output(
        ["gh", "api", f"repos/{REPOSITORY}/git/ref/heads/main", "-H", "Cache-Control: no-cache"],
        text=True,
        timeout=30,
    )
    ref = json.loads(raw)
    obj = ref.get("object", {})
    if (
        ref.get("ref") != "refs/heads/main"
        or obj.get("type") != "commit"
        or not re.fullmatch(r"[0-9a-f]{40}", str(obj.get("sha", "")))
    ):
        raise RuntimeError("Superseded or invalid current-main identity")
    if obj["sha"] != sha:
        try:
            require_paper_descendant(Path.cwd(), sha, obj["sha"])
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError("Superseded software release: main is not a verified paper-only descendant") from exc
    return sha


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before-software-deploy", action="store_true")
    args = parser.parse_args()
    print(f"Software snapshot current or followed only by verified papers: {require_current_main()}")
    if args.before_software_deploy:
        require_unpublished_software()

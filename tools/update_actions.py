#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
"""Update GitHub Actions in the CI workflow.

This script queries the GitHub API for the latest tag of each action used in
``.github/workflows/ci.yml`` and rewrites the file so ``uses:`` lines point to
that tag along with the corresponding commit SHA in a comment.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"

PATTERN = re.compile(r"^(\s*-?\s*uses:\s*)([^@ ]+)@([^ ]+)(\s*#\s*[0-9a-fA-F]+)?\s*$")


def fetch_latest(owner_repo: str) -> tuple[str, str] | None:
    """Return the newest tag name and commit sha for a GitHub action."""
    url = f"https://api.github.com/repos/{owner_repo}/tags"
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        sys.stderr.write(f"Failed to fetch {url}: {exc}\n")
        return None
    tags = resp.json()
    if not tags:
        return None
    tag = tags[0]
    return tag["name"], tag["commit"]["sha"]


def update() -> bool:
    lines = WORKFLOW.read_text().splitlines()
    changed = False
    for i, line in enumerate(lines):
        m = PATTERN.match(line)
        if not m:
            continue
        prefix, action, current, comment = m.groups()
        if action.startswith("./"):
            continue
        latest = fetch_latest(action)
        if not latest:
            continue
        tag, sha = latest
        new_comment = f" # {sha}"
        if current == tag and comment == new_comment:
            continue
        lines[i] = f"{prefix}{action}@{tag}{new_comment}"
        changed = True
    if changed:
        WORKFLOW.write_text("\n".join(lines) + "\n")
    return changed


def main() -> None:
    if update():
        print("Workflow updated.")
    else:
        print("Workflow already up to date.")


if __name__ == "__main__":
    main()

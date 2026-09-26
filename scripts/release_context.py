# SPDX-License-Identifier: Apache-2.0
"""Reject superseded main runs before deployment or release publication."""

from __future__ import annotations

import json
import os
import re
import subprocess

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"


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
    if ref.get("ref") != "refs/heads/main" or obj.get("type") != "commit" or obj.get("sha") != sha:
        raise RuntimeError("Superseded release run: current main differs from the tested commit")
    return sha


if __name__ == "__main__":
    print(f"Current main verified: {require_current_main()}")

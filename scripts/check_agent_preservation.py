#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Assert no original path disappeared and all original README/flywheel text remains."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import re

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

BASE = "ac9b112a44670f67d53fc3d188ef73fa16e90894"
CI_HEALTH_BADGE = (
    b"https://img.shields.io/github/check-runs/MontrealAI/AGI-Alpha-Agent-v0/main"
    b"?nameFilter=CI%20watchdog&label=CI%20Health&logo=github"
)
SMOKE_BADGE = (
    b"https://img.shields.io/github/check-runs/MontrealAI/AGI-Alpha-Agent-v0/main"
    b"?nameFilter=Smoke%20matrix&label=Smoke%20Test&logo=github"
)
INTEGRATION_BADGE = (
    b"https://img.shields.io/github/check-runs/MontrealAI/AGI-Alpha-Agent-v0/main"
    b"?nameFilter=Integration%20matrix&label=Integration%20CI&logo=github"
)
LIVE_CHECK_BADGES = {"ci-health": CI_HEALTH_BADGE, "smoke": SMOKE_BADGE, "ci": INTEGRATION_BADGE}
BADGE_MAINTENANCE = "CI badge URL queries and the exact live main-commit Health/Smoke/Integration badge URLs only"


def normalize_badge_urls(readme: bytes) -> bytes:
    """Normalize approved live badge URLs; retain every label and all other bytes."""
    # These exact provider URLs read real check runs. A changed repository,
    # branch, check name, static result or forced status color is not an exception.
    for workflow, url in LIVE_CHECK_BADGES.items():
        canonical = f"https://github.com/montrealai/AGI-Alpha-Agent-v0/actions/workflows/{workflow}.yml/badge.svg)"
        readme = readme.replace(url + b")", canonical.encode())
    return re.sub(
        rb"(https://github.com/montrealai/AGI-Alpha-Agent-v0/actions/workflows/"
        rb"(?:pr-ci|ci|smoke|ci-health)\.yml(?:/badge\.svg)?)(?:\?[^)\s]*)?",
        rb"\1",
        readme,
    )


def main() -> None:
    original = subprocess.check_output(["git", "ls-tree", "-r", "-z", "--name-only", BASE]).split(b"\0")
    missing = [p.decode() for p in original if p and not Path(p.decode()).is_file()]
    if missing:
        raise ValueError(f"Original files missing: {missing}")
    readme = subprocess.check_output(["git", "show", f"{BASE}:README.md"])
    if normalize_badge_urls(readme) not in normalize_badge_urls(Path("README.md").read_bytes()):
        raise ValueError("Original README text and every flywheel must remain; only approved CI badge URLs may change")
    if (
        Path("docs/DISCLAIMER_SNIPPET.md").read_bytes()
        != Path("alpha_factory_v1/utils/DISCLAIMER_SNIPPET.md").read_bytes()
    ):
        raise ValueError("packaged project notice differs from the canonical notice")
    for path in Path("contracts").rglob("*.sol"):
        mirror = Path("tests/contracts") / path
        if mirror.exists() and path.read_bytes() != mirror.read_bytes():
            raise ValueError(f"Contract test copy differs from shipped source: {path}")
    print(
        json.dumps(
            {
                "baseline": BASE,
                "original_files_preserved": len(original) - 1,
                "original_readme_text_and_flywheels_preserved": True,
                "permitted_readme_changes": BADGE_MAINTENANCE,
                "contract_copies_match": True,
            }
        )
    )


if __name__ == "__main__":
    main()

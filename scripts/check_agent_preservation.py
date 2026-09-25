#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Assert no original path disappeared and all original README/flywheel text remains."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

BASE = "ac9b112a44670f67d53fc3d188ef73fa16e90894"


def main() -> None:
    original = subprocess.check_output(["git", "ls-tree", "-r", "-z", "--name-only", BASE]).split(b"\0")
    missing = [p.decode() for p in original if p and not Path(p.decode()).is_file()]
    if missing:
        raise ValueError(f"Original files missing: {missing}")
    readme = subprocess.check_output(["git", "show", f"{BASE}:README.md"])
    if readme not in Path("README.md").read_bytes():
        raise ValueError("Original README, including every flywheel, must be retained verbatim")
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
                "original_readme_verbatim": True,
                "contract_copies_match": True,
            }
        )
    )


if __name__ == "__main__":
    main()

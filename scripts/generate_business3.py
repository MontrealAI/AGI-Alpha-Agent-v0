# SPDX-License-Identifier: Apache-2.0
"""Build the enterprise workspace around its preserved original presentation."""
from __future__ import annotations

import json
from pathlib import Path

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path = ROOT) -> None:
    templates = root / "scripts/templates"
    version = json.loads((root / "alpha_factory_v1/demos/catalog.json").read_text())["release"]
    template = (templates / "business3.html").read_text()
    legacy = (templates / "business3-legacy.html").read_text()
    (root / "docs/alpha_agi_business_3_v1/index.html").write_text(
        template.replace("{{VERSION}}", version).replace("{{LEGACY}}", legacy.rstrip("\n"))
    )
    (root / "docs/assets/business3/scenarios.json").write_bytes(
        (root / "alpha_factory_v1/demos/alpha_agi_business_3_v1/scenarios.json").read_bytes()
    )


if __name__ == "__main__":
    build()

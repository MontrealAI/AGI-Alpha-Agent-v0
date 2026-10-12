# SPDX-License-Identifier: Apache-2.0
"""Package the personal SUCCESSOR lab as a reproducible, independent HTML file."""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path


def build(root: Path) -> None:
    """Embed the existing engine, interface, styles and license with exact CSP hashes."""
    source = root / "scripts/templates/successor-pocket"
    engine = (root / "docs/assets/successor/engine.mjs").read_text(encoding="utf-8")
    executable = re.sub(r"^export ", "", engine, flags=re.MULTILINE)
    app = (source / "app.js").read_text(encoding="utf-8")
    script = "\n(() => {\n'use strict';\n" + executable + "\n" + app + "\n})();\n"
    script = script.replace("ENGINE_SOURCE_HASH", hashlib.sha256(engine.encode()).hexdigest())
    style = "\n" + (source / "style.css").read_text(encoding="utf-8") + "\n"
    template = (source / "index.html").read_text(encoding="utf-8")
    for token, value in (("SCRIPT", script), ("STYLE", style)):
        hashed = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        template = template.replace("{{" + token + "_HASH}}", "sha256-" + hashed)
        template = template.replace("{{" + token + "}}", value)
    template = template.replace("{{LICENSE}}", (root / "LICENSE").read_text(encoding="utf-8"))
    destination = root / "docs/successor/play/index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(template, encoding="utf-8")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])

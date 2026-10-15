# SPDX-License-Identifier: Apache-2.0
"""Generate the additive, local-only Alpha discovery entry with exact source hashes."""
from pathlib import Path
import base64
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path = ROOT) -> None:
    paths = ["docs/assets/successor/engine.mjs", "examples/alpha-discovery/engine.mjs"]
    sources = {"scripts/generate_alpha_discovery.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    chunks = []
    for name, relative in zip(("transport", "discovery"), paths):
        source = (root / relative).read_text()
        sources[relative] = hashlib.sha256(source.encode()).hexdigest()
        source = re.sub(
            r"^import .*? from .*?;$", "const {canonical,digest,parseBounded}=transport;", source, flags=re.M
        )
        exports = re.findall(r"^export\s+(?:async\s+)?(?:function|class|const)\s+(\w+)", source, flags=re.M)
        source = re.sub(r"^export\s+", "", source, flags=re.M)
        chunks.append(f"const {name}=(()=>{{\n{source}\nreturn {{{','.join(exports)}}};\n}})();")
    templates = root / "scripts/templates/alpha-discovery"
    for path in sorted(templates.iterdir()):
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    source_hash = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    script = (
        "\n(()=>{\n'use strict';\n"
        + "\n".join(chunks)
        + f"\nconst SOURCE_HASH='{source_hash}';\n"
        + (templates / "app.js").read_text()
        + "\n})();\n"
    )
    if "</script" in script.lower():
        raise ValueError("Closing script tag in source")
    style = "\n" + (templates / "style.css").read_text() + "\n"
    page = (templates / "index.html").read_text()
    for key, value in (("SCRIPT", script), ("STYLE", style)):
        encoded = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        page = page.replace("{{" + key + "_HASH}}", "sha256-" + encoded).replace("{{" + key + "}}", value)
    page = page.replace("{{SOURCE_HASH}}", source_hash)
    if "{{" in page:
        raise ValueError("Unexpanded discovery template")
    destination = root / "docs/successor/discover"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text(page)
    (destination / "sources.json").write_text(
        json.dumps(
            {"schema": "alpha-discovery-source/v1", "sourceHash": source_hash, "sources": sources},
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    build()

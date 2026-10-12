# SPDX-License-Identifier: Apache-2.0
"""Build an offline workshop from the actual Alpha engine and pinned Jobs compiler."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path = ROOT) -> None:
    """Bundle local named ES modules without a dependency or a network request."""
    source = root / "scripts/templates/successor-build"
    vendor = root / "examples/build-successor/vendor/agijobs"
    provenance = json.loads((vendor / "provenance.json").read_text())
    for entry in provenance["files"]:
        actual = hashlib.sha256((vendor / Path(entry["path"]).name).read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise ValueError(f"Pinned AGI Jobs source changed: {entry['path']}")
    modules: dict[Path, str] = {}
    chunks: list[str] = []

    def bundle(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Module outside the repository")
        if path in modules:
            return modules[path]
        name = "module_" + str(len(modules))
        modules[path] = name
        code = path.read_text(encoding="utf-8")

        def replace_import(match: re.Match[str]) -> str:
            binding, relative = match.groups()
            if not relative.startswith("."):
                raise ValueError("Only local source imports are permitted")
            dependency = bundle(path.parent / relative)
            binding = binding.strip()
            if binding.startswith("* as "):
                binding = binding.removeprefix("* as ")
            return f"const {binding} = {dependency};"

        code = re.sub(r"^import\s+([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"];", replace_import, code, flags=re.MULTILINE)
        names = re.findall(r"^export\s+(?:async\s+)?(?:function|const|class)\s+(\w+)", code, flags=re.MULTILINE)
        code = re.sub(r"^export\s+", "", code, flags=re.MULTILINE)
        chunks.append(f"const {name} = (() => {{\n{code}\nreturn {{{', '.join(names)}}};\n}})();")
        return name

    model = bundle(root / "examples/build-successor/model.mjs")
    templates = bundle(vendor / "templates.mjs")
    engine_hash = hashlib.sha256((root / "docs/assets/successor/engine.mjs").read_bytes()).hexdigest()
    script = "\n(() => {\n'use strict';\n" + "\n".join(chunks)
    script += f"\nconst model = {model}, jobsTemplates = {templates};\nconst ENGINE_HASH = '{engine_hash}';\n"
    script += (source / "app.js").read_text(encoding="utf-8") + "\n})();\n"
    if "</script" in script.lower():
        raise ValueError("Unexpected script closing tag in bundle")
    style = "\n" + (source / "style.css").read_text() + "\n"
    directory = json.loads((root / "docs/assets/ecosystem/contracts.json").read_text())
    sections = []
    for key, title in (
        ("alpha", "Alpha Ascension · 5 contracts · 2026-10-11"),
        ("jobs", "AGI Jobs · 24 instances · 2026-10-12"),
    ):
        suite = directory[key]
        cards = []
        for contract in suite["contracts"]:
            address = html.escape(contract["address"])
            cards.append(
                f'<div class="contract"><strong>{html.escape(contract["name"])}</strong>'
                f'<p>{html.escape(contract["purpose"]["en"])} / {html.escape(contract["purpose"]["fr"])}</p>'
                f'<a href="https://etherscan.io/address/{address}#code"><code>{address}</code></a></div>'
            )
        sections.append(
            f'<details><summary>{title}</summary><a class="source" href="{html.escape(suite["source"])}">'
            f'Dated source record / Dossier source daté ↗</a>{"".join(cards)}</details>'
        )
    page = (source / "index.html").read_text(encoding="utf-8")
    for key, content in (("SCRIPT", script), ("STYLE", style)):
        digest = base64.b64encode(hashlib.sha256(content.encode()).digest()).decode()
        page = page.replace("{{" + key + "_HASH}}", "sha256-" + digest)
        page = page.replace("{{" + key + "}}", content)
    proof = {"alphaEngineSha256": engine_hash, "agijobs": provenance}
    for key, value in {
        "CONTRACTS": "\n".join(sections),
        "TOKEN": directory["token"]["address"],
        "PROVENANCE": html.escape(json.dumps(proof, indent=2)),
        "LICENSES": html.escape(
            (root / "LICENSE").read_text() + "\n\nAGI Jobs compiler:\n" + (vendor / "LICENSE").read_text()
        ),
    }.items():
        page = page.replace("{{" + key + "}}", value)
    if "{{" in page:
        raise ValueError("Unexpanded workshop placeholder")
    destination = root / "docs/successor/build/index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    build()

# SPDX-License-Identifier: Apache-2.0
"""Build the public Flywheel simulation and reuse the existing Alpha project codec."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path = ROOT) -> None:
    """Emit one self-contained, CSP-bound document from canonical local sources."""
    names: dict[Path, str] = {}
    sources: dict[str, str] = {}
    chunks: list[str] = []

    def visit(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Flywheel dependencies must remain inside the repository")
        if path in names:
            return names[path]
        name = f"flywheel_module_{len(names)}"
        names[path] = name
        source = path.read_text(encoding="utf-8")
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(source.encode()).hexdigest()

        def imports(match: re.Match[str]) -> str:
            binding, location = match.groups()
            if not location.startswith("."):
                raise ValueError("Only local dependencies may enter the Flywheel bundle")
            return f"const {binding.strip().removeprefix('* as ')} = {visit(path.parent / location)};"

        first_export = re.search(r"^export\s+", source, flags=re.MULTILINE)
        boundary = first_export.start() if first_export else len(source)
        prefix = re.sub(
            r"^import\s+([^;]*?)\s+from\s+['\"]([^'\"]+)['\"];", imports, source[:boundary], flags=re.MULTILINE
        )
        source = prefix + source[boundary:]
        exports = re.findall(r"^export\s+(?:async\s+)?(?:function|class|const)\s+(\w+)", source, flags=re.MULTILINE)
        source = re.sub(r"^export\s+", "", source, flags=re.MULTILINE)
        chunks.append(f"const {name}=(()=>{{\n{source}\nreturn {{{','.join(exports)}}};\n}})();")
        return name

    engine = visit(root / "examples/alpha-flywheel/engine.mjs")
    project = visit(root / "examples/successor-alpha/project.mjs")
    template = root / "scripts/templates/alpha-flywheel"
    for path in [
        *template.iterdir(),
        root / "scripts/generate_alpha_flywheel.py",
        root / "examples/alpha-flywheel/README.md",
        root / "LICENSE",
    ]:
        if path.is_file():
            sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    source_hash = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    code = "\n(()=>{\n'use strict';\n" + "\n".join(chunks)
    code += f"\nconst flywheel={engine},project={project},SOURCE_HASH={json.dumps(source_hash)};\n"
    general_evidence = json.loads((template / "general-evidence.json").read_text(encoding="utf-8"))
    code += "\nconst GENERAL_EVIDENCE=" + json.dumps(general_evidence, ensure_ascii=True, separators=(",", ":")) + ";\n"
    specialist_evidence = json.loads((template / "specialist-evidence.json").read_text(encoding="utf-8"))
    code += (
        "\nconst SPECIALIST_EVIDENCE="
        + json.dumps(specialist_evidence, ensure_ascii=True, separators=(",", ":"))
        + ";\n"
    )
    code += (template / "app.js").read_text(encoding="utf-8") + "\n})();\n"
    if "</script" in code.lower():
        raise ValueError("Closing script tag is forbidden inside the Flywheel bundle")
    style = "\n" + (template / "style.css").read_text(encoding="utf-8") + "\n"
    page = (template / "index.html").read_text(encoding="utf-8")
    for key, value in (("SCRIPT", code), ("STYLE", style)):
        digest = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        page = page.replace("{{" + key + "_HASH}}", "sha256-" + digest).replace("{{" + key + "}}", value)
    page = page.replace("{{SOURCE_HASH}}", source_hash)
    page = page.replace("{{LICENSE}}", html.escape((root / "LICENSE").read_text(encoding="utf-8")))
    if "{{" in page:
        raise ValueError("Unexpanded Flywheel template")
    destination = root / "docs/flywheel"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text(page, encoding="utf-8")
    manifest = {
        "schema": "alpha-flywheel-source/v1",
        "sourceHash": source_hash,
        "sources": sources,
        "pageSha256": hashlib.sha256(page.encode()).hexdigest(),
    }
    (destination / "sources.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    build()

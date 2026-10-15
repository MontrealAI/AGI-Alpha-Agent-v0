# SPDX-License-Identifier: Apache-2.0
"""Build a self-contained, source-bound local mission workspace without network imports."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path = ROOT) -> None:
    names: dict[Path, str] = {}
    sources: dict[str, str] = {
        "scripts/generate_successor_mission.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    }
    chunks: list[str] = []

    def visit(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Module outside repository")
        if path in names:
            return names[path]
        name = f"module_{len(names)}"
        names[path] = name
        source = path.read_text(encoding="utf-8")
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(source.encode()).hexdigest()

        def imports(match: re.Match[str]) -> str:
            binding, location = match.groups()
            if not location.startswith("."):
                raise ValueError("Only local imports are supported")
            return f"const {binding.strip().removeprefix('* as ')} = {visit(path.parent / location)};"

        source = re.sub(r"^import\s+([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"];", imports, source, flags=re.M)
        exports = re.findall(r"^export\s+(?:async\s+)?(?:function|class|const)\s+(\w+)", source, flags=re.M)
        source = re.sub(r"^export\s+", "", source, flags=re.M)
        chunks.append(f"const {name}=(()=>{{\n{source}\nreturn {{{','.join(exports)}}};\n}})();")
        return name

    modules = {}
    for name, path in (
        ("workbench", "examples/successor-workbench/engine.mjs"),
        ("records", "examples/successor-workbench/mission-record.mjs"),
        ("storage", "examples/successor-workbench/mission-store.mjs"),
        ("transport", "docs/assets/successor/engine.mjs"),
        ("projects", "examples/successor-project/engine.mjs"),
        ("projectStorage", "examples/successor-project/store.mjs"),
        ("discovery", "examples/alpha-discovery/engine.mjs"),
    ):
        modules[name] = visit(root / path)
    vendor = root / "examples/build-successor/vendor/agijobs"
    provenance = json.loads((vendor / "provenance.json").read_text())
    for item in provenance["files"]:
        if hashlib.sha256((vendor / Path(item["path"]).name).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Pinned Jobs compiler differs from provenance")
    templates = root / "scripts/templates/successor-mission"
    for path in sorted(templates.iterdir()):
        if path.is_file():
            sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    source_hash = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    code = "\n".join(chunks)
    code += "\n" + "\n".join(f"const {name}={module};" for name, module in modules.items())
    code += f"\nconst SOURCE_HASH='{source_hash}';\n"
    # Verified against GitHub exact commit/path bytes; drift requires a new provenance review.
    native_pins = {
        "examples/alpha-discovery/engine.mjs": "452a25348a3209a99fef9eecbd94bdbfafdc9595777dc5d2bd2a70e9245ea850",
        "examples/successor-workbench/mission-record.mjs": "e80338a4c89905e33b6856189080fd22593a7208b078ddf49a58b296b459ba0f",
    }
    if any(sources[path] != expected for path, expected in native_pins.items()):
        raise ValueError("Native source drift: review commit/path/hash together")
    project_sources = {
        role: {
            "repository": "MontrealAI/AGI-Alpha-Agent-v0",
            "commit": "021b3337de07e9a0cdd105fac967a0dc650de122",
            "path": path,
            "sha256": sources[path],
        }
        for role, path in (
            ("discovery", "examples/alpha-discovery/engine.mjs"),
            ("mission", "examples/successor-workbench/mission-record.mjs"),
        )
    }
    code += "\nconst PROJECT_SOURCES=" + json.dumps(project_sources, sort_keys=True) + ";\n"
    script = (
        "\n(()=>{\n'use strict';\n"
        + code
        + (templates / "app.js").read_text()
        + (templates / "project.js").read_text()
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
        raise ValueError("Unexpanded mission template")
    destination = root / "docs/successor/mission"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text(page)
    (destination / "sources.json").write_text(
        json.dumps(
            {"schema": "successor-mission-source/v1", "sourceHash": source_hash, "sources": sources},
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    build()

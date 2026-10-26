# SPDX-License-Identifier: Apache-2.0
"""Build the browser-local catalogue guide from the released catalogue modules."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path = ROOT) -> None:
    """Embed the exact local dependency closure and an offline worker."""
    names: dict[Path, str] = {}
    sources: dict[str, str] = {}
    chunks: list[str] = []

    def visit(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Guide dependencies must remain in the repository")
        if path in names:
            return names[path]
        name = f"ti_module_{len(names)}"
        names[path] = name
        source = path.read_text(encoding="utf-8")
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(source.encode()).hexdigest()

        def imports(match: re.Match[str]) -> str:
            binding, location = match.groups()
            if not location.startswith("."):
                raise ValueError("Guide dependencies must be local")
            return f"const {binding.strip().removeprefix('* as ')} = {visit(path.parent / location)};"

        source = re.sub(r"^import\s+([^;]*?)\s+from\s+['\"]([^'\"]+)['\"];", imports, source, flags=re.MULTILINE)
        exports = re.findall(r"^export\s+(?:async\s+)?(?:function|class|const)\s+(\w+)", source, flags=re.MULTILINE)
        source = re.sub(r"^export\s+", "", source, flags=re.MULTILINE)
        chunks.append(f"const {name}=(()=>{{\n{source}\nreturn {{{','.join(exports)}}};\n}})();")
        return name

    guide = visit(root / "examples/ti-guide/guide.mjs")
    planner = visit(root / "examples/ti-guide/planning.mjs")
    template = root / "scripts/templates/ti-guide"
    for path in [*template.iterdir(), Path(__file__).resolve(), root / "LICENSE"]:
        if path.is_file():
            sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    source_hash = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    worker = (
        "\n".join(chunks)
        + f"\nconst guide={guide};\n"
        + """
self.onmessage=async({data})=>{
  try {
    const progress=stage=>self.postMessage({type:'progress',stage});
    const value=data.kind==='restore'
      ? await guide.restoreWorkspace(data.raw,data.sourceHash,progress)
      : await guide.compute(data.input,progress);
    self.postMessage({type:'result',value});
  } catch(error) {self.postMessage({type:'error',message:error.message});}
};
"""
    )
    code = "\n(()=>{\n'use strict';\n" + "\n".join(chunks)
    code += f"\nconst guide={guide},planner={planner},SOURCE_HASH={json.dumps(source_hash)};\n"
    code += "const WORKER_SOURCE=" + json.dumps(worker, ensure_ascii=False) + ";\n"
    code += (template / "app.js").read_text(encoding="utf-8") + "\n})();\n"
    if "</script" in code.lower():
        raise ValueError("Closing script tag in executable guide")
    style = "\n" + (template / "style.css").read_text(encoding="utf-8") + "\n"
    page = (template / "index.html").read_text(encoding="utf-8")
    for key, value in (("SCRIPT", code), ("STYLE", style)):
        hashed = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        page = page.replace("{{" + key + "_HASH}}", "sha256-" + hashed).replace("{{" + key + "}}", value)
    page = page.replace("{{LICENSE}}", html.escape((root / "LICENSE").read_text(encoding="utf-8")))
    if "{{" in page:
        raise ValueError("Unexpanded catalogue guide template")
    destination = root / "docs/try"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text(page, encoding="utf-8")
    manifest = {
        "schema": "ti-guide-source/v1",
        "sourceHash": source_hash,
        "sources": sources,
        "pageSha256": hashlib.sha256(page.encode()).hexdigest(),
    }
    (destination / "sources.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    build()

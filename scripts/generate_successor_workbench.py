# SPDX-License-Identifier: Apache-2.0
"""Bundle the canonical work adapters for the browser and installed native operator."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def bundle(root: Path = ROOT) -> tuple[str, str, str]:
    """Resolve only repository-local modules and verify pinned Jobs source bytes."""
    vendor = root / "examples/build-successor/vendor/agijobs"
    provenance = json.loads((vendor / "provenance.json").read_text())
    for item in provenance["files"]:
        if hashlib.sha256((vendor / Path(item["path"]).name).read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Pinned Jobs compiler source differs from its provenance")
    names: dict[Path, str] = {}
    sources: dict[str, str] = {}
    chunks: list[str] = []

    def visit(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Module is outside the repository")
        if path in names:
            return names[path]
        name = f"module_{len(names)}"
        names[path] = name
        source = path.read_text(encoding="utf-8")
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(source.encode()).hexdigest()

        def imports(match: re.Match[str]) -> str:
            binding, location = match.groups()
            if not location.startswith("."):
                raise ValueError("Only local imports are allowed")
            binding = binding.strip().removeprefix("* as ")
            return f"const {binding} = {visit(path.parent / location)};"

        source = re.sub(r"^import\s+([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"];", imports, source, flags=re.M)
        exports = re.findall(r"^export\s+(?:async\s+)?(?:function|class|const)\s+(\w+)", source, flags=re.M)
        source = re.sub(r"^export\s+", "", source, flags=re.M)
        chunks.append(f"const {name}=(()=>{{\n{source}\nreturn {{{','.join(exports)}}};\n}})();")
        return name

    engine = visit(root / "examples/successor-workbench/engine.mjs")
    transport = visit(root / "docs/assets/successor/engine.mjs")
    native = visit(root / "examples/successor-workbench/native.mjs")
    source_hash = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    code = "\n".join(chunks) + f"\nconst workbench={engine},transport={transport},nativeWorkbench={native};\n"
    code += f"const SOURCE_HASH='{source_hash}';\n"
    return code, source_hash, json.dumps(sources, sort_keys=True)


def build(root: Path = ROOT) -> None:
    """Produce identical domain logic in both delivery formats."""
    code, source_hash, sources = bundle(root)
    package = root / "alpha_factory_v1/core/runtime/successor"
    worker = "// SPDX-License-Identifier: Apache-2.0\n// Generated; edit examples/successor-workbench/engine.mjs.\n"
    worker += code
    worker += """
let raw='';
process.stdin.setEncoding('utf8');
for await (const chunk of process.stdin) {
  raw+=chunk;
  if(Buffer.byteLength(raw)>2000000)throw Error('INPUT_SIZE_LIMIT');
}
const request=transport.parseBounded(raw);
let result;
if(request.operation==='registry')result={schema:nativeWorkbench.VERSION,sourceHash:SOURCE_HASH,families:nativeWorkbench.REGISTRY};
else if(request.operation==='example')result=nativeWorkbench.example(request.family);
else if(request.operation==='run')result=await nativeWorkbench.run(request.spec,{sourceHash:SOURCE_HASH});
else if(request.operation==='plan')result=await nativeWorkbench.plan(request.spec);
else if(request.operation==='inspect')result=await nativeWorkbench.inspectPack(request.pack);
else throw Error('UNKNOWN_OPERATION');
process.stdout.write(transport.canonical(result)+'\\n');
"""
    # The module closure is shared with the browser. Bind the complete native
    # program separately so dispatch, limits and emitted wrapper changes cannot
    # resume unfinished work under an unchanged module-only identity.
    worker_bytes = worker.encode("utf-8")
    (package / "workbench_worker.mjs").write_bytes(worker_bytes)
    manifest = {
        "schema": "successor-workbench-source/v1",
        "sourceHash": source_hash,
        "workerSHA256": hashlib.sha256(worker_bytes).hexdigest(),
        "sources": json.loads(sources),
    }
    (package / "workbench_sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
    licenses = (
        (root / "LICENSE").read_text()
        + "\nAGI Jobs compiler:\n"
        + (root / "examples/build-successor/vendor/agijobs/LICENSE").read_text()
    )
    (package / "workbench_LICENSE.txt").write_text(licenses)
    templates = root / "scripts/templates/successor-workbench"
    if not (templates / "index.html").exists():
        return
    script = "\n(()=>{\n'use strict';\n" + code + (templates / "app.js").read_text() + "\n})();\n"
    if "</script" in script.lower():
        raise ValueError("Closing script tag in generated source")
    style = "\n" + (templates / "style.css").read_text() + "\n"
    page = (templates / "index.html").read_text()
    for key, value in (("SCRIPT", script), ("STYLE", style)):
        hashed = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        page = page.replace("{{" + key + "_HASH}}", "sha256-" + hashed).replace("{{" + key + "}}", value)
    page = page.replace("{{SOURCE_HASH}}", source_hash)
    import html

    page = page.replace("{{LICENSES}}", html.escape(licenses))
    if "{{" in page:
        raise ValueError("Unexpanded workbench template")
    destination = root / "docs/successor/work/index.html"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")


if __name__ == "__main__":
    build()

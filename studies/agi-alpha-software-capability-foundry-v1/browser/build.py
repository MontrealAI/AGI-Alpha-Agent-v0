# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def build() -> dict[str, object]:
    names = ["index.html", "style.css", "app.mjs", "adapter.mjs", "example-data.json"]
    names += [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "vendor").rglob("*")) if p.is_file()]
    files = {name: {"sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), "bytes": (ROOT / name).stat().st_size} for name in names}
    source_hash = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    manifest = {"schema": "foundry-browser-source/v1", "sourceHash": source_hash, "files": files}
    (ROOT / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    modules: dict[Path, str] = {}
    chunks: list[str] = []
    visiting: set[Path] = set()
    pattern = re.compile(r"(?m)^import\s+([\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"]\s*;")

    def bundle(path: Path) -> str:
        path = path.resolve()
        if path in modules:
            return modules[path]
        if path in visiting or not path.is_relative_to(ROOT):
            raise ValueError("Unsupported circular or external browser dependency")
        visiting.add(path)
        text = path.read_text()

        def dependency(match: re.Match[str]) -> str:
            binding, name = match.groups()
            if not name.startswith("."):
                raise ValueError("Only local static imports may be bundled")
            target = bundle(path.parent / name)
            if binding.startswith("* as "):
                return "const " + binding[5:].strip() + " = " + target + ";"
            if not binding.startswith("{") or not binding.endswith("}"):
                raise ValueError("Unsupported import declaration")
            binding = re.sub(r"\b([A-Za-z_$][\w$]*)\s+as\s+([A-Za-z_$][\w$]*)\b", r"\1: \2", binding)
            return "const " + binding + " = " + target + ";"

        text = pattern.sub(dependency, text)
        exports = re.findall(r"(?m)^export\s+(?:async\s+)?(?:const|let|var|class|function)\s+([A-Za-z_$][\w$]*)", text)
        text = re.sub(r"(?m)^export\s+", "", text)
        if re.search(r"(?m)^import\s|\bimport\s*\(", text):
            raise ValueError("Unresolved import remains")
        label = "foundryModule" + str(len(modules))
        modules[path] = label
        chunks.append("const " + label + " = (()=>{\n" + text + "\nreturn Object.freeze({" + ",".join(exports) + "});\n})();")
        visiting.remove(path)
        return label

    bundle(ROOT / "app.mjs")
    javascript = "'use strict';\n" + "\n".join(chunks)
    recorded = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "downloads").glob("*")) if p.is_file()]
    resources = {name: base64.b64encode((ROOT / name).read_bytes()).decode() for name in [*names, "source-manifest.json", "vendor-manifest.json", "research.json", "README.md", *recorded]}
    html = (ROOT / "index.html").read_text().replace('<link rel="stylesheet" href="style.css">', "<style>" + (ROOT / "style.css").read_text() + "</style>")
    embedded = '<script type="application/json" id="foundry-embedded-resources">' + json.dumps(resources, separators=(",", ":")) + "</script>"
    html = html.replace('<script type="module" src="app.mjs"></script>', embedded + "\n<script>" + javascript.replace("</script", "<\\/script") + "</script>")
    output = ROOT / "Foundry_Lab.html"
    output.write_text(html)
    record = {"schema": "foundry-standalone-build/v1", "sourceHash": source_hash, "bundledModules": len(modules), "packaging": "Unminified lexical module wrappers; original static module files embedded byte-exact for source inspection. This is a packaging transform, not an unchanged executable file.", "standaloneSha256": hashlib.sha256(output.read_bytes()).hexdigest(), "bytes": output.stat().st_size,
              "recordedEvidence": {name: {"sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), "bytes": (ROOT / name).stat().st_size} for name in recorded},
              "researchSha256": hashlib.sha256((ROOT / "research.json").read_bytes()).hexdigest()}
    (ROOT / "standalone-build.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))

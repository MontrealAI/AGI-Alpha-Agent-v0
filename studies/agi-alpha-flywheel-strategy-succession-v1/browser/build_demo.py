"""Build one offline HTML from the exact local browser/scientific source closure."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
IMPORTS = re.compile(r"^import\s+[\s\S]*?\s+from\s+(['\"])([^'\"]+)\1\s*;", re.M)
modules: dict[str, str] = {}


def include(path: Path) -> None:
    """Capture an inert, statically imported module inside the companion tree."""
    path = path.resolve()
    key = path.relative_to(BASE).as_posix()
    if key in modules:
        return
    source = path.read_text(encoding="utf-8")
    modules[key] = source
    for match in IMPORTS.finditer(source):
        target = match.group(2)
        if not target.startswith("."):
            raise ValueError(f"External import is not permitted in offline bundle: {key}: {target}")
        include(path.parent / target)


def encoded(value: object) -> str:
    """Keep source text inert inside an HTML JSON script element."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(
        "\u2028", "\\u2028"
    ).replace("\u2029", "\\u2029")


include(ROOT / "app.mjs")
manifest = {key: hashlib.sha256(value.encode()).hexdigest() for key, value in sorted(modules.items())}
source_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
execution_manifest = dict(manifest)
execution_manifest["browser/bootstrap.mjs"] = hashlib.sha256((ROOT / "bootstrap.mjs").read_bytes()).hexdigest()
execution_hash = hashlib.sha256(
    json.dumps(execution_manifest, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
recorded_path = ROOT / "recorded-summary.json"
recorded = json.loads(recorded_path.read_text()) if recorded_path.exists() else None
data = {
    "schema": "strategy-succession-browser-bundle/v1",
    "source_hash": source_hash,
    "execution_source_hash": execution_hash,
    "execution_manifest": execution_manifest,
    "module_manifest": manifest,
    "upstream_commit": "c352bad0a0941fdccd490a7224e3efd1b8de45d5",
    "upstream_release": "v1.42.0",
    "research": recorded,
    "scope": "Fresh finite demonstration, separate from the frozen confirmatory campaign and installed native runtime.",
}
page = (ROOT / "template.html").read_text().replace("__STYLES__", (ROOT / "styles.css").read_text())
page = page.replace("__BUNDLE_DATA__", encoded(data)).replace("__BUNDLE_MODULES__", encoded(modules))
page = page.replace("__BOOTSTRAP__", (ROOT / "bootstrap.mjs").read_text())
output = ROOT / "index.html"
output.write_text(page, encoding="utf-8")
record = {
    "schema": "strategy-succession-browser-manifest/v1",
    "source_hash": source_hash,
    "execution_source_hash": execution_hash,
    "execution_manifest": execution_manifest,
    "modules": manifest,
    "presentation": {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ("template.html", "styles.css", "build_demo.py")
    },
    "output": output.name,
    "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    "bytes": output.stat().st_size,
    "research_embedded": recorded is not None,
}
(ROOT / "BUNDLE_MANIFEST.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({key: record[key] for key in ("source_hash", "output_sha256", "bytes", "research_embedded")}))

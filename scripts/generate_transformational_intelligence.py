# SPDX-License-Identifier: Apache-2.0
"""Build the offline, bounded public-source understanding experiment."""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def render(root: Path = ROOT) -> tuple[str, dict[str, Any]]:
    """Bundle the local source-clause engine and UI with exact CSP hashes."""
    template = root / "scripts/templates/transformational-intelligence"
    engine_path = root / "docs/assets/transformational-intelligence/source-understanding.mjs"
    native_engine_path = root / "docs/assets/successor/engine.mjs"
    inspector_path = root / "examples/transformational-intelligence/inspector.mjs"
    modules: dict[Path, str] = {}
    chunks: list[str] = []

    def bundle(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Bundled sources must stay within the repository")
        if path in modules:
            return modules[path]
        name = f"ti_module_{len(modules)}"
        modules[path] = name
        source = path.read_text(encoding="utf-8")

        def imports(match: re.Match[str]) -> str:
            binding, location = match.groups()
            if not location.startswith("."):
                raise ValueError("Only repository-local modules may enter the offline bundle")
            binding = binding.strip().removeprefix("* as ")
            return f"const {binding} = {bundle(path.parent / location)};"

        # Imports embedded in the existing reusable-tool source string are data.
        first_export = re.search(r"^export\s+", source, flags=re.MULTILINE)
        boundary = first_export.start() if first_export else 0
        source = (
            re.sub(r"^import\s+([^;]*?)\s+from\s+['\"]([^'\"]+)['\"];", imports, source[:boundary], flags=re.MULTILINE)
            + source[boundary:]
        )
        reexports: list[str] = []
        reexport = re.search(r"^export\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"];", source, flags=re.MULTILINE)
        if reexport:
            names, location = reexport.groups()
            reexports = [name.strip() for name in names.split(",")]
            replacement = f"const {{{names}}} = {bundle(path.parent / location)};"
            source = source[: reexport.start()] + replacement + source[reexport.end() :]
        exports = re.findall(r"^export\s+(?:async\s+)?(?:function|class|const)\s+(\w+)", source, flags=re.MULTILINE)
        exports.extend(reexports)
        source = re.sub(r"^export\s+", "", source, flags=re.MULTILINE)
        chunks.append(f"const {name}=(()=>{{\n{source}\nreturn {{{','.join(exports)}}};\n}})();")
        return name

    inspector = bundle(inspector_path)
    bridge = bundle(root / "examples/transformational-intelligence/project-bridge.mjs")
    native_engine = modules[native_engine_path.resolve()]
    engine = engine_path.read_text(encoding="utf-8")
    engine = re.sub(r"^export\s+", "", engine, flags=re.MULTILINE)
    script = (
        "\n(()=>{\n'use strict';\n"
        + "\n".join(chunks)
        + f"\nconst inspectNative={inspector}.inspectTransformationEnvelope,nativeCanonical={native_engine}.canonical,assertNativePublic={inspector}.assertPublicContent;\n"
        + f"const tiProject={bridge};\n"
        + engine
        + "\n"
        + (template / "app.js").read_text(encoding="utf-8")
        + "\n})();\n"
    )
    style = "\n" + (template / "style.css").read_text(encoding="utf-8") + "\n"
    if "</script" in script.lower():
        raise ValueError("Closing script tag is forbidden in bundled source")
    page = (template / "index.html").read_text(encoding="utf-8")
    vendor = root / "examples/transformational-intelligence/vendor/fleet"
    notices = "Fleet project module and nested Manager safe-data module. Both retain the following MIT license.\n\n" + (
        vendor / "LICENSE"
    ).read_text(encoding="utf-8")
    page = page.replace("{{THIRD_PARTY_NOTICES}}", html.escape(notices))
    for name, value in (("SCRIPT", script), ("STYLE", style)):
        digest = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        page = page.replace("{{" + name + "_HASH}}", "sha256-" + digest).replace("{{" + name + "}}", value)
    if "{{" in page:
        raise ValueError("Unexpanded experiment template")
    sources = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [
            engine_path,
            *modules,
            *sorted(template.iterdir()),
            root / "scripts/generate_transformational_intelligence.py",
            vendor / "SOURCE.json",
            vendor / "LICENSE",
            vendor / "fleet/successor/vendor/manager/LICENSE",
        ]
        if path.is_file()
    }
    manifest = {
        "schema_version": "ti-browser-source/v1",
        "sources": sources,
        "page_sha256": hashlib.sha256(page.encode()).hexdigest(),
        "scope": "Deterministic local structural coverage; independent review pending; no authority",
    }
    return page, manifest


def build(root: Path = ROOT) -> None:
    """Write the exact authoritative render without altering its portable bytes."""
    page, manifest = render(root)
    destination = root / "docs/transformational-intelligence"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text(page, encoding="utf-8")
    (destination / "sources.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()

# SPDX-License-Identifier: Apache-2.0
"""Build the additive, self-contained capability-development workspace with pinned CSP."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(root: Path = ROOT) -> None:
    """Bundle only fixed repository modules; never user-authored code."""
    names: dict[Path, str] = {}
    sources: dict[str, str] = {}
    chunks: list[str] = []

    def visit(path: Path) -> str:
        path = path.resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Module outside repository")
        if path in names:
            return names[path]
        name = f"capability_module_{len(names)}"
        names[path] = name
        source = path.read_text(encoding="utf-8")
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(source.encode()).hexdigest()

        def imports(match: re.Match[str]) -> str:
            binding, location = match.groups()
            if not location.startswith("."):
                raise ValueError("Only local imports are supported")
            binding = binding.strip().removeprefix("* as ")
            if binding.startswith("{"):
                binding = re.sub(r"\b(\w+)\s+as\s+(\w+)\b", r"\1: \2", binding)
            return f"const {binding} = {visit(path.parent / location)};"

        source = re.sub(r"^import\s+([^;]*?)\s+from\s+['\"]([^'\"]+)['\"];", imports, source, flags=re.MULTILINE)
        exports = re.findall(
            r"^export\s+(?:async\s+)?(?:function\s*\*?|class|const)\s+(\w+)", source, flags=re.MULTILINE
        )
        source = re.sub(r"^export\s+", "", source, flags=re.MULTILINE)
        chunks.append(f"const {name}=(()=>{{\n{source}\nreturn {{{','.join(exports)}}};\n}})();")
        return name

    modules = {
        "capability": visit(root / "examples/successor-capability/workspace.mjs"),
        "storage": visit(root / "examples/successor-workbench/mission-store.mjs"),
        "outEvolve": visit(root / "examples/successor-capability/out-evolve-workspace.mjs"),
        "outEvolveConstructor": visit(root / "examples/successor-capability/constructor.mjs"),
        "outEvolvePackages": visit(root / "examples/successor-capability/capability-package.mjs"),
        "outEvolveApparatus": visit(root / "examples/successor-capability/apparatus.mjs"),
        "outEvolveEvaluation": visit(root / "examples/successor-capability/evaluation.mjs"),
        "discoveryLab": visit(root / "examples/successor-capability/discovery-lab.mjs"),
        "discoveryHistory": visit(root / "examples/successor-capability/discovery-lab-history.mjs"),
        "discoveryContract": visit(root / "examples/successor-capability/discovery-lab-contract.mjs"),
        "discoveryEvidence": visit(root / "examples/successor-capability/discovery-lab-evidence-history.mjs"),
        "discoveryFuture": visit(root / "examples/successor-capability/discovery-lab-future.mjs"),
        "discoveryDocket": visit(root / "examples/successor-capability/discovery-lab-docket.mjs"),
        "discoveryReceipts": visit(root / "examples/successor-capability/discovery-lab-receipts.mjs"),
        "discoveryDeployments": visit(root / "examples/successor-capability/discovery-lab-deployments.mjs"),
        "discoveryRealTask": visit(root / "examples/successor-capability/discovery-lab-real-task.mjs"),
        "outExecute": visit(root / "examples/successor-capability/out-execute/engine.mjs"),
        "outExecuteModel": visit(root / "examples/successor-capability/out-execute/model.mjs"),
        "outExecuteFixtures": visit(root / "examples/successor-capability/out-execute/fixtures.mjs"),
        "outExecuteTransport": visit(root / "examples/successor-capability/out-execute/transport.mjs"),
    }
    deployment_path = root / "docs/discovery-lab/DEPLOYMENT_COMPATIBILITY.json"
    deployment_bytes = deployment_path.read_bytes()
    deployment_inventory = json.loads(deployment_bytes)
    sources[deployment_path.relative_to(root).as_posix()] = hashlib.sha256(deployment_bytes).hexdigest()
    templates = root / "scripts/templates/successor-capability"
    for path in [root / "scripts/generate_successor_capability.py", *sorted(templates.iterdir())]:
        if path.is_file():
            sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    source_hash = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    discovery_sources = {
        "modelDigest": sources["examples/successor-capability/discovery-lab.mjs"],
        "evaluatorDigest": sources["examples/successor-capability/discovery-lab-checker.mjs"],
        "sourceDigest": source_hash,
    }
    script = "\n(()=>{\n'use strict';\n" + "\n".join(chunks)
    script += "\n" + "\n".join(f"const {name}={value};" for name, value in modules.items())
    script += f"\nconst SOURCE_HASH='{source_hash}';\n" + (templates / "app.js").read_text()
    script += "\n" + (templates / "out-evolve-app.js").read_text()
    script += "\nconst DISCOVERY_SOURCES=" + json.dumps(discovery_sources, sort_keys=True) + ";\n"
    script += (templates / "discovery-lab-app.js").read_text() + "\n"
    script += (templates / "discovery-lab-bridge.js").read_text() + "\n"
    script += "\nconst DEPLOYMENT_INVENTORY=" + json.dumps(deployment_inventory, sort_keys=True) + ";\n"
    real_task_hash = sources["examples/successor-capability/discovery-lab-real-task.mjs"]
    script += (
        "\nconst REAL_TASK_SOURCES="
        + json.dumps({"adapterSourceDigest": real_task_hash, "checkerSourceDigest": real_task_hash}, sort_keys=True)
        + ";\n"
    )
    script += (templates / "discovery-lab-continuation.js").read_text() + "\n})();\n"
    if "</script" in script.lower():
        raise ValueError("Closing script tag in source")
    style = "\n" + (templates / "style.css").read_text() + "\n" + (templates / "discovery-lab.css").read_text() + "\n"
    page = (templates / "index.html").read_text()
    page = page.replace(
        '    <section id="out-evolve"',
        (templates / "discovery-lab.html").read_text() + '\n    <section id="out-evolve"',
        1,
    )
    for key, value in (("SCRIPT", script), ("STYLE", style)):
        encoded = base64.b64encode(hashlib.sha256(value.encode()).digest()).decode()
        page = page.replace("{{" + key + "_HASH}}", "sha256-" + encoded).replace("{{" + key + "}}", value)
    page = page.replace("{{SOURCE_HASH}}", source_hash)
    if "{{" in page:
        raise ValueError("Unexpanded capability template")
    destination = root / "docs/successor/capabilities"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.html").write_text(page)
    (destination / "sources.json").write_text(
        json.dumps(
            {"schema": "successor-capability-source/v1", "sourceHash": source_hash, "sources": sources},
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    build()

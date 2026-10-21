# SPDX-License-Identifier: Apache-2.0
"""Reproduce the exact portable bundle and protect its separate acceptance lane."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
from types import ModuleType

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_portable_bundle_reproduces_and_gallery_preserves_exact_bytes() -> None:
    manifest = json.loads((ROOT / "docs/successor/capabilities/sources.json").read_text())
    with tempfile.TemporaryDirectory(prefix="capability-delivery-") as directory:
        isolated = Path(directory)
        for name in manifest["sources"]:
            target = isolated / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        load_script("generate_successor_capability").build(isolated)
        for name in ("index.html", "sources.json"):
            assert (isolated / "docs/successor/capabilities" / name).read_bytes() == (
                ROOT / "docs/successor/capabilities" / name
            ).read_bytes(), name
        page = isolated / "docs/successor/capabilities/index.html"
        original = page.read_bytes()
        load_script("generate_gallery_html").insert_back_link([page])
        assert page.read_bytes() == original


def test_acceptance_is_mandatory_read_only_and_retains_evidence() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/successor-capability.yml").read_text())
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["group"].startswith("capability-")
    job = workflow["jobs"]["capability"]
    assert "if" not in job and not job.get("continue-on-error")
    steps = job["steps"]
    for step in steps:
        if "uses" in step:
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
    commands = [
        "node --test examples/successor-capability/*.test.mjs",
        "python scripts/generate_successor_capability.py",
        "git diff --exit-code -- docs/successor/capabilities",
        "python tests/browser/test_successor_capability_browser.py",
    ]
    for command in commands:
        matches = [step for step in steps if command in step.get("run", "")]
        assert len(matches) == 1
        assert "if" not in matches[0] and not matches[0].get("continue-on-error")
    browser = next(step for step in steps if step.get("run") == commands[-1])
    assert browser["env"]["AXE_SCRIPT"].endswith("/tests/browser/node_modules/axe-core/axe.min.js")
    uploader = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert uploader["if"] == "always()"
    assert uploader["with"]["if-no-files-found"] == "error"

# SPDX-License-Identifier: Apache-2.0
"""Bind complete native worker semantics without changing browser/source identities."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from scripts import generate_successor_workbench as generator

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = Path("alpha_factory_v1/core/runtime/successor")
PAGE = Path("docs/successor/work/index.html")


def _source_copy(destination: Path) -> Path:
    """Copy the actual build inputs only; no generated worker or manifest."""
    _, _, sources = generator.bundle(ROOT)
    vendor = Path("examples/build-successor/vendor/agijobs")
    provenance = json.loads((ROOT / vendor / "provenance.json").read_text())
    paths = {
        "LICENSE",
        "scripts/generate_successor_workbench.py",
        str(vendor / "LICENSE"),
        str(vendor / "provenance.json"),
        *json.loads(sources),
        *(str(vendor / Path(item["path"]).name) for item in provenance["files"]),
        *("scripts/templates/successor-workbench/" + name for name in ("app.js", "index.html", "style.css")),
    }
    for name in paths:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    (destination / PACKAGE).mkdir(parents=True)
    return destination


def _manifest(root: Path) -> dict[str, object]:
    manifest = json.loads((root / PACKAGE / "workbench_sources.json").read_text())
    assert isinstance(manifest, dict)
    return manifest


def test_complete_worker_identity_reproduces_shipped_bytes(tmp_path: Path) -> None:
    root = _source_copy(tmp_path / "source")
    generator.build(root)
    worker = (root / PACKAGE / "workbench_worker.mjs").read_bytes()
    manifest = _manifest(root)
    assert manifest["workerSHA256"] == hashlib.sha256(worker).hexdigest()
    assert worker == (ROOT / PACKAGE / "workbench_worker.mjs").read_bytes()
    assert manifest == _manifest(ROOT)
    assert (root / PAGE).read_bytes() == (ROOT / PAGE).read_bytes()
    first = {name: (root / PACKAGE / name).read_bytes() for name in ("workbench_worker.mjs", "workbench_sources.json")}
    generator.build(root)
    assert first == {name: (root / PACKAGE / name).read_bytes() for name in first}


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("if(Buffer.byteLength(raw)>2000000)", "if(Buffer.byteLength(raw)>2000001)"),
        (
            "else if(request.operation==='plan')result=await nativeWorkbench.plan(request.spec);",
            "else if(request.operation==='plan')result=await workbench.plan(request.spec);",
        ),
    ],
    ids=["input-limit", "native-dispatch"],
)
def test_wrapper_changes_identity_with_same_module_sources(tmp_path: Path, before: str, after: str) -> None:
    root = _source_copy(tmp_path / "source")
    generator.build(root)
    original = _manifest(root)
    original_worker = (root / PACKAGE / "workbench_worker.mjs").read_bytes()
    original_page = (root / PAGE).read_bytes()
    script = root / "scripts/generate_successor_workbench.py"
    text = script.read_text()
    assert text.count(before) == 1
    script.write_text(text.replace(before, after), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("changed_workbench_generator", script)
    assert spec is not None and spec.loader is not None
    changed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(changed)
    changed.build(root)
    current = _manifest(root)
    current_worker = (root / PACKAGE / "workbench_worker.mjs").read_bytes()
    assert current_worker != original_worker
    assert current["workerSHA256"] == hashlib.sha256(current_worker).hexdigest()
    assert current["workerSHA256"] != original["workerSHA256"]
    assert current["sourceHash"] == original["sourceHash"]
    assert current["sources"] == original["sources"]
    assert (root / PAGE).read_bytes() == original_page

# SPDX-License-Identifier: Apache-2.0
"""Reproduce the exact portable bundle and protect its separate acceptance lane."""

from __future__ import annotations

import importlib.util
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
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
    # Standalone and reusable release invocations must not cancel one another.
    assert "${{ github.workflow }}" in workflow["concurrency"]["group"]
    job = workflow["jobs"]["capability"]
    assert job["if"] == "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}"
    assert job["needs"] == "paper-scope"
    assert workflow["jobs"]["paper-scope"]["uses"] == "./.github/workflows/paper-scope.yml"
    assert not job.get("continue-on-error")
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
    browser = next(step for step in steps if commands[-1] in step.get("run", ""))
    assert browser["env"]["AXE_SCRIPT"].endswith("/tests/browser/node_modules/axe-core/axe.min.js")
    retained = {
        commands[0]: "node.log",
        "tests/test_successor_capability_delivery.py -q": "delivery.log",
        "python -m mypy --strict": "typing.log",
        commands[-1]: "v1-browser.log",
        "python tests/browser/test_out_evolve_browser.py": "out-evolve-browser.log",
        "python tests/browser/test_out_execute_browser.py": "out-execute-browser.log",
        "node examples/successor-capability/out-execute/reproduce.mjs": "out-execute-study.log",
        "python tests/browser/test_successor_capability_accessibility.py": "accessibility-review.log",
    }
    for command, log in retained.items():
        step = next(step for step in steps if command in step.get("run", ""))
        assert "set -o pipefail" in step["run"]
        assert f"tee capability-evidence/logs/{log}" in step["run"]
        assert "if" not in step and not step.get("continue-on-error")
    typing = next(step["run"] for step in steps if "python -m mypy --strict" in step.get("run", ""))
    assert "tests/browser/out_evolve_recovery.py" in typing
    assert "tests/browser/test_out_execute_browser.py" in typing
    events = workflow.get("on", workflow.get(True))
    assert "tests/browser/out_evolve_recovery.py" in events["pull_request"]["paths"]
    assert "tests/browser/test_out_execute_browser.py" in events["pull_request"]["paths"]
    assert "workflow_call" in events
    node_step = next(step["run"] for step in steps if "node --test" in step.get("run", ""))
    assert "examples/successor-capability/out-execute/*.test.mjs" in node_step
    uploader = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert uploader["if"] == "always()"
    assert uploader["with"]["if-no-files-found"] == "error"


def test_release_packaging_requires_the_same_complete_capability_gate() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/agent-release.yml").read_text())
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["successor-capability"]
    assert job == {
        "if": "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}",
        "needs": ["paper-scope", "publication-preflight"],
        "uses": "./.github/workflows/successor-capability.yml",
    }
    package = workflow["jobs"]["package"]
    assert "successor-capability" in package["needs"]
    assert package["if"] == "${{ !cancelled() && success() && needs.paper-scope.outputs.mode == 'full' }}"
    assert not package.get("continue-on-error")
    download = next(step for step in package["steps"] if step.get("uses", "").startswith("actions/download-artifact@"))
    assert download["with"]["pattern"] == "!{historical-ci,release-package,public-pages,github-pages}*"
    assert download["with"]["digest-mismatch"] == "error"


def test_retained_authored_study_is_bound_to_installed_source_and_keeps_counterbaselines() -> None:
    record = json.loads((ROOT / "docs/agent/release-evidence/out-execute-authored-study-20261021.json").read_text())
    summary = record["summary"]
    assert record["scope"] == "local-authored-finite-study-not-release-acceptance"
    assert summary["manuscriptCompanionReproduced"] is False
    for group in ("compilerSources", "checkerSources"):
        for path, expected in summary["source"][group].items():
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    for path, expected in record["studyHarnessSources"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    assert summary["snapshots"] == summary["matches"] == 576
    assert summary["semanticStops"] == 160 != summary["manuscriptClaimCounts"]["semanticStops"]
    assert summary["executionWork"] == summary["matchedIncrementalWork"]
    assert summary["identicalInputControl"]["fixedSecond"] < summary["identicalInputControl"]["boundarySecond"]
    assert summary["localArchiveReopenAudit"]["profileComparisons"] > 0
    assert len(record["retainedFixtureSha256"]) == summary["fixtures"] == 64

# SPDX-License-Identifier: Apache-2.0
"""Inert exporter reconstruction regressions; no browser or generated-code execution."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def authored_export() -> dict[str, Any]:
    """Call fixed reviewed modules; all generated module strings remain inert."""
    script = """
import {readFileSync} from 'node:fs';
const root = process.argv[1];
const {createJoinMission} = await import(new URL('examples/successor-alpha/engine.mjs', root));
const {discoverStrategy} = await import(new URL('examples/successor-alpha/research.mjs', root));
const {buildPlanCapability} = await import(new URL('examples/successor-alpha/capability.mjs', root));
const {computeInstalledSourceHash} = await import(new URL('examples/successor-alpha/native-cli.mjs', root));
const {canonical} = await import(new URL('docs/assets/successor/engine.mjs', root));
const inputs = {leftCsv:'sku,name,price\\nA,"Alpha, one",10\\nA,=SUM(1),11\\nZ,Missing,0\\n',
    rightCsv:'id,name,price\\nA,"Alpha, one",10\\nA,Other,12\\nY,New,3\\n',leftKey:'sku',rightKey:'id'};
const mission = createJoinMission(inputs), sourceHash = await computeInstalledSourceHash();
const report = await discoverStrategy(mission, {sourceHash,maxAuxiliaryRows:64,auxiliaryWeight:0,confirmationSeed:17});
const transported = JSON.parse(canonical(report));
const read = name => readFileSync(new URL(name, root), 'utf8').replace(/\\r\\n?/g, '\\n');
const options = {sourceHash,engineSource:read('examples/successor-alpha/engine.mjs'),
    researchSource:read('examples/successor-alpha/research.mjs')};
const browserContext = await buildPlanCapability(mission, report, options);
const oldReconstruction = await buildPlanCapability(mission, transported, options);
process.stdout.write(JSON.stringify({inputs,strategy:transported,
    originalReportCanonical:canonical(report),transportedReportCanonical:canonical(transported),
    browserBytes:Buffer.from(browserContext).toString('base64'),
    oldBytes:Buffer.from(oldReconstruction).toString('base64')}));
"""
    result = subprocess.run(
        [os.environ.get("NODE_EXECUTABLE", "node"), "--input-type=module", "-e", script, ROOT.as_uri() + "/"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


@pytest.fixture
def browser_boundary(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Load only helpers; invoking any browser is an explicit regression failure."""
    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        SimpleNamespace(
            Browser=object,
            BrowserContext=object,
            Page=object,
            Response=object,
            expect=SimpleNamespace(set_options=lambda **_kwargs: None),
            sync_playwright=lambda: pytest.fail("This regression must not start a browser"),
        ),
    )
    path = ROOT / "tests/browser/test_successor_alpha_browser.py"
    spec = importlib.util.spec_from_file_location("inert_capability_reconstruction_boundary", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_transport_requires_trusted_original_report_reconstruction(authored_export, browser_boundary):
    fixture = authored_export
    assert fixture["originalReportCanonical"] == fixture["transportedReportCanonical"]
    original = base64.b64decode(fixture["browserBytes"], validate=True)
    old = base64.b64decode(fixture["oldBytes"], validate=True)
    assert original != old, "The fixture must reproduce the old full-byte refusal"
    assert len(original) == len(old)
    rebuilt = browser_boundary.expected_plan_tool(fixture["inputs"], fixture["strategy"])
    assert rebuilt == original
    assert hashlib.sha256(rebuilt).digest() != hashlib.sha256(old).digest()


def test_old_mismatch_is_retained_and_never_reaches_host(
    authored_export, browser_boundary, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    original = base64.b64decode(authored_export["browserBytes"], validate=True)
    old = base64.b64decode(authored_export["oldBytes"], validate=True)
    monkeypatch.setattr(browser_boundary, "expected_plan_tool", lambda *_args: old)
    monkeypatch.setattr(
        browser_boundary.subprocess, "run", lambda *_a, **_k: pytest.fail("Mismatched bytes reached host")
    )
    with pytest.raises(AssertionError, match="Downloaded capability differs"):
        browser_boundary.execute_verified_plan_tool(
            original, authored_export["inputs"], authored_export["strategy"], {}, str(tmp_path), [], [], tmp_path
        )
    assert not (tmp_path / "retained.mjs").exists()
    diagnostic = json.loads((tmp_path / "capability-export-byte-comparison.json").read_text())
    assert diagnostic["equal"] is False
    assert diagnostic["downloaded_sha256"] == hashlib.sha256(original).hexdigest()
    assert diagnostic["expected_sha256"] == hashlib.sha256(old).hexdigest()
    offset = diagnostic["first_differing_byte"]
    assert original[:offset] == old[:offset] and original[offset] != old[offset]
    assert len(diagnostic["downloaded_context_hex"]) <= 96 and len(diagnostic["expected_context_hex"]) <= 96
    assert {p.name for p in tmp_path.iterdir()} == {"capability-export-byte-comparison.json"}


def test_corrected_exact_bytes_only_present_trusted_reconstruction_to_inert_host(
    authored_export, browser_boundary, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    original = base64.b64decode(authored_export["browserBytes"], validate=True)
    trusted = browser_boundary.expected_plan_tool(authored_export["inputs"], authored_export["strategy"])
    monkeypatch.setattr(browser_boundary, "expected_plan_tool", lambda *_args: trusted)
    calls = []

    def inert(argv, **kwargs):
        calls.append(argv)
        assert (tmp_path / "retained.mjs").read_bytes() == trusted == original
        assert kwargs["timeout"] == 30
        return subprocess.CompletedProcess(argv, 0, stdout="{}", stderr="")

    monkeypatch.setattr(browser_boundary.subprocess, "run", inert)
    result = browser_boundary.execute_verified_plan_tool(
        original, authored_export["inputs"], authored_export["strategy"], {}, str(tmp_path), [], [], tmp_path
    )
    assert result.returncode == 0 and len(calls) == 1
    diagnostic = json.loads((tmp_path / "capability-export-byte-comparison.json").read_text())
    assert diagnostic["equal"] is True and diagnostic["first_differing_byte"] is None
    assert diagnostic["downloaded_context_hex"] == diagnostic["expected_context_hex"] == ""


@pytest.mark.parametrize("field", ["schema", "source", "budget", "weight", "seed", "retained_plan"])
def test_forged_report_or_unbounded_parameters_refuse_before_capability_export(
    authored_export, browser_boundary, field: str
):
    report = json.loads(json.dumps(authored_export["strategy"]))
    if field == "schema":
        report["schema"] = "unsupported"
    elif field == "source":
        report["sourceHash"] = "0" * 64
    elif field == "budget":
        report["objective"]["maxAuxiliaryRows"] = 4501
    elif field == "weight":
        report["objective"]["auxiliaryWeight"] = 1000001
    elif field == "seed":
        report["confirmation"]["seed"] = 2**32
    else:
        report["decision"]["retainedPlan"]["guard"]["op"] = "run_unreviewed_code"
    with pytest.raises(subprocess.CalledProcessError):
        browser_boundary.expected_plan_tool(authored_export["inputs"], report)

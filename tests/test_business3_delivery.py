# SPDX-License-Identifier: Apache-2.0
"""Exercise the documented notebook, container launcher and release evidence."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import pytest

from alpha_factory_v1.demos.alpha_agi_business_3_v1.enterprise import artifacts, read_json, verify
from scripts import business3_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/alpha_agi_business_3_v1"


def test_documentation_generator_runs_without_an_installed_package(tmp_path: Path) -> None:
    """The historical gallery calls scripts directly from a clean source checkout."""
    for relative in (
        "scripts/generate_business3.py",
        "scripts/templates/business3.html",
        "scripts/templates/business3-legacy.html",
        "alpha_factory_v1/demos/catalog.json",
        "alpha_factory_v1/demos/alpha_agi_business_3_v1/scenarios.json",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (tmp_path / "docs/alpha_agi_business_3_v1").mkdir(parents=True)
    (tmp_path / "docs/assets/business3").mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(tmp_path / "scripts/generate_business3.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    page = (tmp_path / "docs/alpha_agi_business_3_v1/index.html").read_text()
    assert 'id="b3-app"' in page and 'id="chart"' in page and "{{LEGACY}}" not in page
    assert (tmp_path / "docs/assets/business3/scenarios.json").read_bytes() == (DEMO / "scenarios.json").read_bytes()


def test_notebook_executes_all_maintained_cells_against_actual_checkout(tmp_path: Path) -> None:
    notebook = json.loads((DEMO / "colab_alpha_agi_business_3_demo.ipynb").read_text())
    code = "\n\n".join("".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code")
    env = {**os.environ, "BUSINESS3_SOURCE": str(ROOT), "BUSINESS3_OUTPUT": str(tmp_path / "evidence")}
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, cwd=tmp_path, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    paths = list((tmp_path / "evidence").glob("*/dossier.json"))
    assert len(paths) == 1
    report = verify(read_json(paths[0], 2_000_000))
    assert report["result"]["portfolio"]["expectedNpvUsd"] == 648579
    with zipfile.ZipFile(paths[0].parent.with_suffix(".zip")) as bundle:
        assert {name: bundle.read(name) for name in bundle.namelist()} == artifacts(report)


def test_shell_launcher_forwards_case_and_retains_output_without_tty_or_credentials(tmp_path: Path) -> None:
    binary = tmp_path / "docker"
    log = tmp_path / "calls.jsonl"
    binary.write_text(
        f"#!{sys.executable}\nimport json,sys\nfrom pathlib import Path\n"
        f"with Path({str(log)!r}).open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n"
    )
    binary.chmod(0o755)
    output = tmp_path / "output with spaces"
    result = subprocess.run(
        ["bash", str(DEMO / "run_business_3_demo.sh"), "--case", "lean-budget", "--output-dir", str(output)],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}", "OPENAI_API_KEY": "never-forward-this"},
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls[0] == ["info"]
    assert calls[1][-1] == str(ROOT)
    run = calls[2]
    assert run[:2] == ["run", "--rm"]
    assert run[run.index("--network") + 1] == "none"
    assert "--read-only" in run and "-it" not in run and "-e" not in run
    assert run[run.index("-v") + 1] == f"{output}:/output"
    assert run[-4:] == ["--case", "lean-budget", "--output", "/output"]
    assert "never-forward-this" not in log.read_text()


@pytest.fixture(scope="module")
def accepted_receipt() -> dict:
    return {
        "schema": evidence.SCHEMA,
        "passed": True,
        "commit": "a" * 40,
        "version": "1.13.0",
        "origin": "https://montrealai.github.io/AGI-Alpha-Agent-v0/",
        "browser_errors": [],
        "http_failures": [],
        "checks": sorted(evidence.CHECKS),
        "assets": evidence.asset_hashes(),
        "cases": evidence.expected_cases(),
    }


def test_release_receipt_requires_exact_source_cases_and_assets(accepted_receipt: dict) -> None:
    evidence.verify_report(accepted_receipt, "a" * 40, "1.13.0", accepted_receipt["origin"])


@pytest.mark.parametrize(
    "change",
    [
        "commit",
        "version",
        "origin",
        "case-hash",
        "case-status",
        "case-omitted",
        "asset-hash",
        "checks",
        "passed",
        "browser_errors",
        "http_failures",
    ],
)
def test_stale_or_incomplete_public_evidence_blocks_publication(accepted_receipt: dict, change: str) -> None:
    report = deepcopy(accepted_receipt)
    if change == "case-hash":
        report["cases"][0]["sha256"] = "0" * 64
    elif change == "case-status":
        report["cases"][0]["status"] = "APPROVED"
    elif change == "case-omitted":
        report["cases"].pop()
    elif change == "asset-hash":
        report["assets"][evidence.ASSETS[0]] = "0" * 64
    elif change == "checks":
        report["checks"].remove("axe-wcag-a-aa-no-violations")
    elif change == "passed":
        report["passed"] = False
    elif change in ("browser_errors", "http_failures"):
        report[change] = ["failure"]
    else:
        report[change] = "stale"
    with pytest.raises(ValueError, match="Business 3"):
        evidence.verify_report(report, "a" * 40, "1.13.0", accepted_receipt["origin"])

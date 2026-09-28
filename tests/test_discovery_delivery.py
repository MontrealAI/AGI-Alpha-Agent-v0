# SPDX-License-Identifier: Apache-2.0
"""Check discovery delivery, preservation and exact public acceptance boundaries."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import discovery_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/alpha_agi_insight_v0"


def test_generator_runs_without_an_installed_package(tmp_path: Path) -> None:
    for relative in (
        "scripts/generate_discovery.py",
        "scripts/templates/discovery.html",
        "scripts/templates/discovery-original.html",
        "alpha_factory_v1/demos/catalog.json",
        "alpha_factory_v1/demos/alpha_agi_insight_v0/scenarios.json",
        "alpha_factory_v1/demos/alpha_agi_insight_v0/discovery.py",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (tmp_path / "docs/alpha_agi_insight_v0").mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(tmp_path / "scripts/generate_discovery.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    page = (tmp_path / "docs/alpha_agi_insight_v0/index.html").read_text()
    assert 'id="workspace"' in page and 'id="ranking"' in page and "{{VERSION}}" not in page
    assert (tmp_path / "docs/assets/discovery/scenarios.json").read_bytes() == (DEMO / "scenarios.json").read_bytes()


def test_original_research_bytes_remain_intact() -> None:
    expected = [
        ("RESEARCH_ARCHIVE.md", "d8229ccaf8eded0009fbe846d9d152f0f59550381f2f6001ca763be414b1f329"),
        ("research_notebook_archive.ipynb", "00122ac0bcd1d14452cce1f692f1fa0fae78cd73cf8c3bb432000163d31681cd"),
    ]
    for name, value in expected:
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == value, name


@pytest.fixture(scope="module")
def accepted_receipt() -> dict:
    return {
        "schema": evidence.SCHEMA,
        "passed": True,
        "commit": "a" * 40,
        "version": "1.15.0",
        "origin": "https://montrealai.github.io/AGI-Alpha-Agent-v0/",
        "browser_errors": [],
        "http_failures": [],
        "checks": sorted(evidence.CHECKS),
        "assets": evidence.asset_hashes(),
        "cases": evidence.expected_cases(),
    }


def test_release_receipt_requires_exact_source_cases_and_assets(accepted_receipt: dict) -> None:
    evidence.verify_report(accepted_receipt, "a" * 40, "1.15.0", accepted_receipt["origin"])


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
    with pytest.raises(ValueError, match="Insight discovery"):
        evidence.verify_report(report, "a" * 40, "1.15.0", accepted_receipt["origin"])

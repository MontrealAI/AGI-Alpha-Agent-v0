# SPDX-License-Identifier: Apache-2.0
"""Check governance delivery, preservation and exact public acceptance boundaries."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import governance_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/solving_agi_governance"


def test_generator_runs_without_an_installed_package(tmp_path: Path) -> None:
    for relative in (
        "scripts/generate_governance.py",
        "scripts/templates/governance.html",
        "scripts/templates/governance-legacy.html",
        "alpha_factory_v1/demos/catalog.json",
        "alpha_factory_v1/demos/solving_agi_governance/scenarios.json",
        "alpha_factory_v1/demos/solving_agi_governance/workbench.py",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (tmp_path / "docs/solving_agi_governance").mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(tmp_path / "scripts/generate_governance.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    page = (tmp_path / "docs/solving_agi_governance/index.html").read_text()
    assert 'id="gov-app"' in page and 'id="chart"' in page and "{{LEGACY}}" not in page
    assert (tmp_path / "docs/assets/governance/scenarios.json").read_bytes() == (DEMO / "scenarios.json").read_bytes()


def test_original_research_bytes_remain_intact() -> None:
    expected = (
        ("RESEARCH_ARCHIVE.md", "c83ddedcd7badd86a9024ffeec5063652a30c134634669313b3f9fbded420011"),
        ("research_notebook_archive.ipynb", "0bb2530d911e39fd9c6b0cec508298fb0d83fc4631e619b544e45256df2bf015"),
        ("alpha_asi_governance_v13.pdf", "f94b1b21007015532ef0930523438465f842211ba36c107271b89ae6868eab28"),
        ("alpha_asi_governance_v13.tex", "0e784e9826c9013c6435fd7e1eee49b74e29ff8d747777850c44d54d37e8f8ac"),
        (
            "presentation/Solving_Alpha-AGI_Governance_v0.pdf",
            "e9f86339e9924b8417af6bdae55bae1e6536073d5f242796f297302e752b0830",
        ),
        (
            "presentation/Solving_Alpha-AGI_Governance_v0.pptx",
            "9959183c237cfe345eb0241acabbab91dc93977adf9f8cb59dcc98ecfaf5690a",
        ),
    )
    for name, value in expected:
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == value, name


@pytest.fixture(scope="module")
def accepted_receipt() -> dict:
    return {
        "schema": evidence.SCHEMA,
        "passed": True,
        "commit": "a" * 40,
        "version": "1.14.0",
        "origin": "https://montrealai.github.io/AGI-Alpha-Agent-v0/",
        "browser_errors": [],
        "http_failures": [],
        "checks": sorted(evidence.CHECKS),
        "assets": evidence.asset_hashes(),
        "cases": evidence.expected_cases(),
    }


def test_release_receipt_requires_exact_source_cases_and_assets(accepted_receipt: dict) -> None:
    evidence.verify_report(accepted_receipt, "a" * 40, "1.14.0", accepted_receipt["origin"])


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
    with pytest.raises(ValueError, match="Governance"):
        evidence.verify_report(report, "a" * 40, "1.14.0", accepted_receipt["origin"])

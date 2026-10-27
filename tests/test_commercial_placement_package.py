# SPDX-License-Identifier: Apache-2.0
"""Named scope, independent acceptance and usable artifact export boundaries."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.successor.flywheel_experiments import solve_placement, verify_placement
from alpha_factory_v1.core.runtime.successor.protocol import digest
from contrib.resilient_placement_delivery.report import checked_delivery, render_pack
from contrib.resilient_placement_delivery.schema import parse_brief

EXAMPLES = Path(__file__).resolve().parents[1] / "contrib/resilient_placement_delivery/examples"


def brief() -> dict[str, Any]:
    return json.loads((EXAMPLES / "bilingual-publishing.json").read_text())


def receipt(raw: dict[str, Any]) -> dict[str, Any]:
    scope = parse_brief(raw)
    outcome = solve_placement(scope.problem)
    content = {
        "problem": scope.problem.model_dump(),
        "outcome": outcome,
        "verification": verify_placement(scope.problem, outcome),
        "executed_locally": True,
    }
    return {
        "mission": {
            "mission_id": scope.brief_id,
            "beneficiary": scope.beneficiary,
            "mode": "hybrid",
            "components": {"model": "simulated", "tools": "executed-local"},
            "inputs": {
                "problem": scope.problem.model_dump(),
                "placement_brief_digest": digest("commercial-placement-brief", scope.model_dump()),
            },
        },
        "profile": {"model_id": "scripted-protocol-fixture/v1"},
        "status": "delivered-awaiting-independent-acceptance-and-costs",
        "actions": 1,
        "history": [{"type": "function_call_output", "output": json.dumps(content)}],
        "result": {
            "deliverable": outcome,
            "artifacts": [
                {"kind": "placement-result", "content": content, "digest": digest("placement-artifact", content)}
            ],
        },
    }


@pytest.mark.parametrize("name", ["bilingual-publishing.json", "regional-analysis.json"])
def test_fresh_named_pack_has_exact_files_and_loads(name: str, tmp_path: Path) -> None:
    raw = json.loads((EXAMPLES / name).read_text())
    evidence = receipt(raw)
    result = render_pack(raw, evidence, tmp_path / "pack")
    directory = tmp_path / "pack"
    assert not (directory / "INCOMPLETE").exists()
    for path, entry in result["manifest"]["files"].items():
        data = (directory / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"] and len(data) == entry["bytes"]
    plan = result["delivery"]["plan"]
    assert len(plan) == 2 * len(raw["services"])
    assert sum(row["objective_cost"] for row in plan) == result["delivery"]["outcome"]["cost"]
    assert all(host["remaining"] >= 0 for host in result["delivery"]["hosts"])
    page = (directory / "index.html").read_text()
    assert 'lang="fr"' in page and 'lang="en"' in page and 'href="plan.csv"' in page
    assert "Research acceptance, not customer acceptance" in page and "USD0" in page
    assert "<script" not in page and "http://" not in page and "https://" not in page
    assert json.loads((directory / "brief.json").read_text())["brief_id"] == raw["brief_id"]
    with pytest.raises(FileExistsError):
        render_pack(raw, evidence, directory)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate-host",
        "duplicate-service",
        "missing-cost",
        "extra-cost",
        "float",
        "boolean",
        "authority",
        "budget",
        "blank",
        "unknown",
    ],
)
def test_bad_intake_refuses(change: str) -> None:
    raw = brief()
    if change == "duplicate-host":
        raw["hosts"][1]["id"] = raw["hosts"][0]["id"]
    elif change == "duplicate-service":
        raw["services"][1]["id"] = raw["services"][0]["id"]
    elif change == "missing-cost":
        raw["services"][0]["costs"].pop("quebec-primary")
    elif change == "extra-cost":
        raw["services"][0]["costs"]["unknown"] = 5
    elif change in {"float", "boolean"}:
        raw["hosts"][0]["capacity"] = 5.0 if change == "float" else True
    elif change == "authority":
        raw["authorized_inputs"] = 1
    elif change == "budget":
        raw["services"] *= 2
        for index, service in enumerate(raw["services"]):
            service["id"] = f"s{index}"
    elif change == "blank":
        raw["beneficiary"] = "   "
    else:
        raw["unapproved_tool"] = "deploy"
    with pytest.raises(ValueError):
        parse_brief(raw)


@pytest.mark.parametrize(
    "change",
    ["name", "rights", "problem", "artifact", "answer", "incomplete", "observation", "no-action", "live-label"],
)
def test_tampered_or_unsupported_delivery_never_publishes(change: str, tmp_path: Path) -> None:
    raw = brief()
    evidence = receipt(raw)
    if change == "name":
        raw["hosts"][0]["id"] = "renamed-host"
        for service in raw["services"]:
            service["costs"]["renamed-host"] = service["costs"].pop("quebec-primary")
    elif change == "rights":
        raw["rights_basis"] = "Different rights statement"
    elif change == "problem":
        evidence["mission"]["inputs"]["problem"]["capacities"][0] += 1
    elif change == "artifact":
        evidence["result"]["artifacts"][0]["digest"] = "0" * 64
    elif change == "answer":
        evidence["result"]["deliverable"]["cost"] += 1
    elif change == "incomplete":
        evidence["result"]["deliverable"]["status"] = "incomplete"
    elif change == "observation":
        evidence["history"] = []
    elif change == "no-action":
        evidence["actions"] = 0
    else:
        evidence["mission"]["components"]["model"] = "live"
    with pytest.raises(ValueError):
        render_pack(raw, evidence, tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_export_safely_quotes_untrusted_labels(tmp_path: Path) -> None:
    raw = brief()
    raw["services"][0]["id"] = '=HYPERLINK("https://example.invalid")'
    raw["beneficiary"] = '<script>alert("x")</script> & research'
    result = render_pack(raw, receipt(raw), tmp_path / "safe")
    page = (tmp_path / "safe/index.html").read_text()
    assert "<script>" not in page and "&lt;script&gt;" in page and "&amp; research" in page
    rows = list(csv.DictReader(io.StringIO((tmp_path / "safe/plan.csv").read_text())))
    dangerous = [row for row in rows if "HYPERLINK" in row["service"]]
    assert dangerous and all(row["service"].startswith("'=") for row in dangerous)
    assert result["delivery"]["actual_complete_cost_micro_usd"] is None


def test_proven_infeasibility_is_not_a_fake_plan(tmp_path: Path) -> None:
    raw = brief()
    for host in raw["hosts"]:
        host["capacity"] = 1
    result = render_pack(raw, receipt(raw), tmp_path / "infeasible")
    assert result["delivery"]["outcome"]["status"] == "infeasible"
    assert result["delivery"]["plan"] == []
    assert all(host["load"] is None for host in result["delivery"]["hosts"])
    assert "No plan is issued" in (tmp_path / "infeasible/index.html").read_text()


def test_source_intake_mutation_is_detached() -> None:
    raw = brief()
    frozen = parse_brief(raw)
    old = copy.deepcopy(frozen.problem.model_dump())
    raw["hosts"][0]["capacity"] += 1
    assert frozen.problem.model_dump() == old

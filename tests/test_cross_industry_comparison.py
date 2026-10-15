# SPDX-License-Identifier: Apache-2.0
"""Behavior, evidence and failure boundaries for the supplied-input comparator."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from alpha_factory_v1.demos.cross_industry_alpha_factory import opportunity_comparison as comparison
from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as legacy

MODULE = "alpha_factory_v1.demos.cross_industry_alpha_factory.opportunity_comparison"


@pytest.fixture
def supplied():
    return comparison.load_input(comparison.EXAMPLE)


def test_exact_ranking_evidence_and_no_mutation(supplied):
    original = copy.deepcopy(supplied)
    with patch("socket.socket", side_effect=AssertionError("network forbidden")):
        report = comparison.compare_opportunities(supplied)
    assert supplied == original
    assert report == comparison.compare_opportunities(supplied)
    assert report["selected_id"] == "routing"
    assert report["input_sha256"] == "86b650902fb51267afbd4ed00a556f8638ae75bb1446ceda4c2b5504181a3658"
    assert [(r["id"], r["score"], r["rank"]) for r in report["ranking"]] == [
        ("routing", 74.5, 1),
        ("maintenance", 73.5, 2),
        ("storage", 52.5, None),
    ]
    assert report["ranking"][0]["contributions"] == {"benefit": 26, "confidence": 25.5, "effort": 15, "risk": 8}
    assert report["ranking"][2]["exclusion_reasons"] == ["risk exceeds max_risk", "confidence below min_confidence"]
    assert report["ranking"][0]["evidence"] == supplied["opportunities"][1]["evidence"]
    assert [r["pareto_optimal"] for r in report["ranking"]] == [True, True, False]


def test_changes_to_supplied_priorities_change_result(supplied):
    supplied["weights"] = dict(benefit=100, confidence=0, effort=0, risk=0)
    assert comparison.compare_opportunities(supplied)["selected_id"] == "maintenance"
    supplied["constraints"] = dict(max_risk=100, min_confidence=0)
    assert comparison.compare_opportunities(supplied)["selected_id"] == "storage"


def test_all_excluded_no_winner(supplied):
    supplied["constraints"] = dict(max_risk=0, min_confidence=100)
    report = comparison.compare_opportunities(supplied)
    assert report["selected_id"] is None
    assert all(r["rank"] is None and not r["pareto_optimal"] for r in report["ranking"])
    assert [r["id"] for r in report["ranking"]] == ["maintenance", "routing", "storage"]


def test_ties_ascii_and_duplicate_vectors(supplied):
    row = supplied["opportunities"][0]
    supplied["opportunities"] = [{**row, "id": "z"}, {**row, "id": "A"}]
    report = comparison.compare_opportunities(supplied)
    assert [r["id"] for r in report["ranking"]] == ["A", "z"]
    assert all(r["pareto_optimal"] for r in report["ranking"])
    supplied["opportunities"][0]["effort"] += 1
    assert not comparison.compare_opportunities(supplied)["ranking"][1]["pareto_optimal"]


def test_exact_half_up_rounding():
    assert comparison._round_ratio(1, 128) == 0.007813
    assert comparison._round_ratio(0, 3) == 0
    assert comparison._round_ratio(1, 3) == 0.333333


@pytest.mark.parametrize("invalid", [-1, 101, 1.0, True, None, "50", float("nan"), float("inf")])
@pytest.mark.parametrize("target", ["rating", "weight", "constraint"])
def test_invalid_numbers(supplied, invalid, target):
    obj, key = {
        "rating": (supplied["opportunities"][0], "benefit"),
        "weight": (supplied["weights"], "benefit"),
        "constraint": (supplied["constraints"], "max_risk"),
    }[target]
    obj[key] = invalid
    with pytest.raises(ValueError):
        comparison.compare_opportunities(supplied)


@pytest.mark.parametrize("invalid", ["", " padded", "a\n", "\ud800", "x\x80", "x" * 501, "\ufeffx", "x\ufeff"])
def test_invalid_text(supplied, invalid):
    supplied["opportunities"][0]["opportunity"] = invalid
    with pytest.raises(ValueError):
        comparison.compare_opportunities(supplied)


def test_structure_failures(supplied):
    mutations = [
        lambda d: d.update(extra=1),
        lambda d: d.update(schema_version="unknown"),
        lambda d: d.update(opportunities=[]),
        lambda d: d.update(opportunities=d["opportunities"] * 34),
        lambda d: d["weights"].update(benefit=0, confidence=0, effort=0, risk=0),
        lambda d: d["opportunities"][0].update(id="bad id"),
        lambda d: d["opportunities"][0].update(id="routing"),
        lambda d: d["opportunities"][0].update(evidence=[]),
        lambda d: d["opportunities"][0].update(evidence=["note"] * 11),
        lambda d: d["constraints"].update(typo=1),
    ]
    for mutate in mutations:
        data = copy.deepcopy(supplied)
        mutate(data)
        with pytest.raises(ValueError):
            comparison.compare_opportunities(data)


@pytest.mark.parametrize(
    "raw",
    [b'{"schema_version":1,"schema_version":2}', b"\xff", b"[" * 2000, b" " * (1024 * 1024 + 1)],
    ids=["duplicate", "utf8", "depth", "size"],
)
def test_cli_invalid_no_success_output(tmp_path, raw):
    path = tmp_path / "bad.json"
    path.write_bytes(raw)
    result = subprocess.run([sys.executable, "-m", MODULE, "--input", str(path)], capture_output=True)
    assert result.returncode == 2
    assert not result.stdout
    assert b"Invalid input:" in result.stderr


def test_cli_explicit_input_required_and_example_reproducible(tmp_path):
    env = {**os.environ, "HOME": str(tmp_path), "OPENAI_API_KEY": "must-not-be-used"}
    missing = subprocess.run([sys.executable, "-m", MODULE], capture_output=True, env=env)
    assert missing.returncode == 2
    command = [sys.executable, "-m", MODULE, "--example"]
    a = subprocess.run(command, capture_output=True, env=env)
    b = subprocess.run(command, capture_output=True, env=env)
    assert a.returncode == b.returncode == 0
    assert a.stdout == b.stdout
    assert json.loads(a.stdout)["mode"] == "synthetic-example"
    assert not (tmp_path / ".alpha_factory").exists()


def test_legacy_no_implicit_findings_or_provider_fallback():
    with pytest.raises(ValueError, match="explicit"):
        legacy.discover_alpha()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "present"}):
        assert legacy.discover_alpha(sample=True, seed=1) == [legacy.SAMPLE_ALPHA[1]]
        with patch.object(legacy, "openai", create=True) as provider:
            provider.chat.completions.create.side_effect = RuntimeError("offline")
            with pytest.raises(ValueError, match="no sample fallback"):
                legacy.discover_alpha(generate=True)


def test_queue_only_eligible_and_dry_run(supplied):
    from alpha_factory_v1.demos.cross_industry_alpha_factory.queue_cross_alpha import queue_opportunities

    with patch("socket.socket", side_effect=AssertionError("network forbidden")):
        jobs = queue_opportunities(10, supplied=supplied, dry_run=True)
    assert len(jobs) == 2
    assert "delivery routes" in jobs[0]["note"]


def test_queue_cli_rejects_malformed_input_without_traceback(tmp_path, capsys):
    from alpha_factory_v1.demos.cross_industry_alpha_factory.queue_cross_alpha import main

    path = tmp_path / "invalid.json"
    path.write_bytes(b'{"bad":')
    with pytest.raises(SystemExit) as error:
        main(["--input", str(path), "--dry-run"])
    assert error.value.code == 2
    stderr = capsys.readouterr().err
    assert stderr.startswith("Invalid input:") and "Traceback" not in stderr

# SPDX-License-Identifier: Apache-2.0
"""Behavioral and adversarial acceptance for actual future-task transfer."""

from __future__ import annotations

from copy import deepcopy
import io
import json
from pathlib import Path
import zipfile

import pytest

from alpha_factory_v1.core.runtime import transfer as t
from alpha_factory_v1.core.runtime.cli import main


def reviewed(scenario: str = "seasonal") -> dict:
    return t.review_run(t.run(t.example(scenario)), "accept", "Operator", "Inspected raw predictions", 2000, 3000)


def test_actual_transfer_and_failure_are_not_scripted_verdicts() -> None:
    for scenario, state in [("seasonal", "accepted"), ("shift", "hold"), ("ablation", "hold")]:
        report = reviewed(scenario)
        assert t.verify(report)["bounded_transfer"] == state
        assert t.verify(report)["manuscript_promotion"] == "hold"
        assert report["core"]["capability"]["policy"] == "seasonal-5"
        assert report["core"]["evidence_contact"]["level"] == "E2"
    ablated = reviewed("ablation")
    assert ablated["core"]["arms"]["B5"] == ablated["core"]["arms"]["B6"]


def test_policy_learning_changes_predictions_and_cannot_see_future_answers() -> None:
    before = t.example()
    after = deepcopy(before)
    after["tasks"][0]["heldout"] = [900] * 8
    a, b = t.compute(before), t.compute(after)
    assert a["capability"] == b["capability"]
    assert a["arms"]["B6"]["tasks"][0]["predictions_milli"] == b["arms"]["B6"]["tasks"][0]["predictions_milli"]
    assert a["metrics"]["raw_gain_milli"] != b["metrics"]["raw_gain_milli"]
    after["training"] = list(range(40))
    assert t.compute(after)["capability"]["policy"] == "linear"
    assert (
        t.compute(after)["arms"]["B6"]["tasks"][0]["predictions_milli"]
        != a["arms"]["B6"]["tasks"][0]["predictions_milli"]
    )


def test_run_does_not_self_accept_and_human_overhead_can_close_gate() -> None:
    specification = t.example()
    specification["human_cost_milli_per_second"] = 100
    report = t.run(specification)
    assert t.verify(report)["bounded_transfer"] == "hold"
    assert t.verify(report)["adjusted_advantage_milli"] is None
    for verdict in ("reject", "repair"):
        assert (
            t.verify(t.review_run(report, verdict, "Operator", "More evidence required", 1, 1))["bounded_transfer"]
            == "hold"
        )
    expensive = t.review_run(report, "accept", "Operator", "Longer treatment review", 1, 86_400_000)
    assert t.verify(expensive)["bounded_transfer"] == "hold"
    spec = t.example()
    spec["call_cost_milli"] = 10000
    assert t.verify(t.review_run(t.run(spec), "accept", "Op", "Reviewed", 1, 1))["bounded_transfer"] == "hold"
    # Self-reported time cannot turn a predictive loss into accepted transfer.
    shift = t.review_run(t.run(t.example("shift")), "accept", "Op", "Reviewed", 86_400_000, 1)
    assert t.verify(shift)["bounded_transfer"] == "hold"


def test_risk_bound_is_enforced() -> None:
    spec = t.example()
    spec["tasks"][0]["heldout"][0] += 1
    spec["risk_limit_milli"] = 0
    report = t.review_run(t.run(spec), "accept", "Operator", "Inspected", 1, 1)
    assert report["core"]["metrics"]["raw_gain_milli"] > 0
    assert not report["core"]["metrics"]["risk_passed"]
    assert t.verify(report)["bounded_transfer"] == "hold"


@pytest.mark.parametrize("mutation", ["prediction", "policy", "gain", "unknown", "stale", "timing", "digest"])
def test_tampering_cannot_be_hidden_by_rehashing(mutation: str) -> None:
    report = reviewed()
    if mutation == "prediction":
        report["core"]["arms"]["B6"]["tasks"][0]["predictions_milli"][0] += 1
    elif mutation == "policy":
        report["core"]["capability"]["policy"] = "last"
    elif mutation == "gain":
        report["core"]["metrics"]["raw_gain_milli"] = 10**9
    elif mutation == "unknown":
        report["validator_verdict"] = "accepted"
    elif mutation == "stale":
        report["review"]["run_sha256"] = "0" * 64
    elif mutation == "timing":
        report["review"]["treatment_ms"] = -1
    else:
        report["sha256"] = "0" * 64
    if mutation in {"prediction", "policy", "gain"}:
        report["sha256"] = t.digest({k: v for k, v in report.items() if k not in {"sha256", "review"}})
        report["review"]["run_sha256"] = report["sha256"]
    with pytest.raises(ValueError):
        t.verify(report)


@pytest.mark.parametrize(
    "raw", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1.5}', '{"x":Infinity}', "[]", '{"x":9007199254740992}']
)
def test_json_import_rejects_ambiguous_documents(raw: str) -> None:
    with pytest.raises(ValueError):
        t.parse(raw)


def test_document_and_spec_bounds() -> None:
    for raw in ('{"x":"' + "a" * t.MAX_BYTES + '"}', '{"x":' + "[" * 25 + "1" + "]" * 25 + "}"):
        with pytest.raises(ValueError):
            t.parse(raw)
    for change in ("duplicate_id", "duplicate_content", "training_overlap", "unknown", "boolean", "policy_prefix"):
        spec = t.example()
        if change == "duplicate_id":
            spec["tasks"][1]["id"] = spec["tasks"][0]["id"]
        elif change == "duplicate_content":
            spec["tasks"][1]["observed"] = spec["tasks"][0]["observed"]
            spec["tasks"][1]["heldout"] = spec["tasks"][0]["heldout"]
        elif change == "training_overlap":
            spec["training"] = list(range(20))
            spec["tasks"][0]["observed"] = list(range(10))
            spec["tasks"][0]["heldout"] = list(range(10, 20))
        elif change == "unknown":
            spec["promotion"] = "accepted"
        elif change == "boolean":
            spec["call_cost_milli"] = True
        else:
            spec["training"] = [1, 90, -34, 57, 11, -45, 31, 17] * 5
        with pytest.raises(ValueError):
            t.compute(spec)


def test_whole_docket_roundtrip_and_file_tampering() -> None:
    report = reviewed()
    data = t.export_docket(report)
    assert t.verify_docket(data) == t.verify(report)
    files = t.docket_files(report)
    assert set(name.split("/")[0] for name in files) == set(t.SECTIONS) | {"checksums.json"}
    for target in ("12_summary_tables/outcome.json", "checksums.json", "../escape.json"):
        altered = dict(files)
        altered[target] = "{}\n"
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for name, content in altered.items():
                archive.writestr(name, content)
        with pytest.raises(ValueError):
            t.verify_docket(stream.getvalue())
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("oversized", "x" * (t.MAX_BYTES + 1))
    with pytest.raises(ValueError):
        t.verify_docket(stream.getvalue())


def test_native_cli_requires_no_identity_and_replays_browser_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    result, reviewed_path, docket = [tmp_path / name for name in ("run.json", "reviewed.json", "docket.zip")]
    assert main(["transfer-run", "--output", str(result)]) == 0
    assert main(["transfer-verify", str(result)]) == 0
    assert (
        main(
            [
                "transfer-review",
                str(result),
                "--decision",
                "accept",
                "--reviewer",
                "Operator",
                "--reason",
                "Reviewed",
                "--control-ms",
                "1000",
                "--treatment-ms",
                "2000",
                "--output",
                str(reviewed_path),
            ]
        )
        == 0
    )
    assert main(["transfer-docket", str(reviewed_path), "--output", str(docket)]) == 0
    assert main(["transfer-verify", str(docket)]) == 0
    assert json.loads(reviewed_path.read_text())["review"]["timing_source"] == "operator-reported"
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(t.example("shift")))
    assert main(["transfer-run", "--spec", str(spec), "--output", str(tmp_path / "shift.json")]) == 0
    result.write_text('{"sha256":"forged"}')
    assert main(["transfer-verify", str(result)]) == 1
    capsys.readouterr()


def test_creation_ledger_counts_actual_forecast_invocations(monkeypatch: pytest.MonkeyPatch) -> None:
    original = t.predict
    calls = 0

    def counted(policy: str, observed: list[int], horizon: int) -> list[int]:
        nonlocal calls
        calls += 1
        return original(policy, observed, horizon)

    monkeypatch.setattr(t, "predict", counted)
    for scenario in ("seasonal", "ablation"):
        calls = 0
        report = t.run(t.example(scenario))
        assert calls == report["observations"]["creation_forecast_calls"]
        assert calls == 2 * report["core"]["metrics"]["validator_forecast_calls"]

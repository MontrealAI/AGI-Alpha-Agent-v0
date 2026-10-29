# SPDX-License-Identifier: Apache-2.0
"""Check metering against actual unchanged native acceptance and adverse inputs."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.retained_experience import verifier
from contrib.retained_experience import verification_scaling as scaling

PANEL = scaling.ROOT / "evidence/retained-experience-20261029/prospective-v1"
SEAL = "a1eee42f8701ebceaa53b88d1f59fd15744121317ce1fcb0df1213529295736c"


@pytest.fixture(scope="module")
def paired_receipts(tmp_path_factory: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    output = tmp_path_factory.mktemp("scaling") / "panel"
    scaling.check_seal(PANEL, SEAL)
    scaling.snapshot_identity(PANEL)
    expected = scaling.derive_panel(PANEL, output, 1, SEAL)
    return scaling.invoke(output, expected, False), scaling.invoke(output, expected, True)


def test_actual_meter_matches_unchanged_native_and_proves_restrictions(
    paired_receipts: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    native, metered = paired_receipts
    scaling.reconcile_pair(native, metered)
    assert native["planned"] == native["accepted"] == 120
    assert metered["meter"]["calls"] == {
        "history_outputs": 9,
        "development_outputs": 54,
        "memory": 1,
        "evaluation_outputs": 120,
    }
    assert metered["meter"]["unclassified_verify_cpu_ns"] >= 0
    assert metered["candidate_write_denied_by_os"] is True
    assert metered["new_socket_denied_by_os"] is True
    assert metered["candidate_imported"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("accepted", 0),
        ("planned", 1),
        ("tasks_hash", "0" * 64),
        ("candidate_imported", True),
        ("new_socket_denied_by_os", False),
    ],
)
def test_false_meter_acceptance_is_rejected(
    paired_receipts: tuple[dict[str, Any], dict[str, Any]],
    field: str,
    value: Any,
) -> None:
    native, original = paired_receipts
    changed = deepcopy(original)
    changed[field] = value
    with pytest.raises(ValueError, match="changed.*acceptance"):
        scaling.reconcile_pair(native, changed)


def test_corrupted_output_is_rejected_by_original_native_checker(tmp_path: Path) -> None:
    output = tmp_path / "panel"
    expected = scaling.derive_panel(PANEL, output, 1, SEAL)
    path = output / "observations.jsonl"
    records = [json.loads(line) for line in path.read_bytes().splitlines()]
    changed = False
    for row in records:
        if row["output"]["artifact"]["status"] == "FEASIBLE":
            row["output"]["duals"] = []
            changed = True
            break
    assert changed
    path.write_bytes(b"\n".join(verifier.canonical(row) for row in records) + b"\n")
    transcript = tmp_path / "refusal.json"
    with pytest.raises(ValueError, match="original verifier refused"):
        scaling.invoke(output, expected, True, transcript)
    failure = verifier.read(transcript)
    assert failure["exit_code"] == 1
    assert json.loads(failure["stdout"])["rejected"]


def test_trusted_seal_and_archived_source_cannot_be_substituted(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="trusted evidence seal"):
        scaling.run(PANEL, "0" * 64, tmp_path / "no-output", 1)
    assert not (tmp_path / "no-output").exists()
    for name in scaling.CRITICAL:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((scaling.ROOT / name).read_bytes() + b"\n")
    with pytest.raises(ValueError, match="archived checker/filter"):
        scaling.snapshot_identity(PANEL, root=tmp_path)


def test_unlisted_archived_startup_code_is_refused(tmp_path: Path) -> None:
    output = tmp_path / "panel"
    scaling.derive_panel(PANEL, output, 1, SEAL)
    (output / "source-snapshot/sitecustomize.py").write_text("raise RuntimeError('unlisted startup code')\n")
    with pytest.raises(ValueError, match="source file set"):
        scaling.snapshot_identity(output)


@pytest.mark.parametrize("count", [0, 17, True])
def test_subset_budget_refuses_before_writing(tmp_path: Path, count: int) -> None:
    with pytest.raises(ValueError, match="bounded source subset"):
        scaling.derive_panel(PANEL, tmp_path / "no-output", count, SEAL)
    assert not (tmp_path / "no-output").exists()


def test_summary_preserves_unknown_costs_and_remainder(
    paired_receipts: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    native, metered = paired_receipts
    result = scaling.summarize(
        [
            {"tasks": 4, "mode": "native", "receipt": native},
            {"tasks": 4, "mode": "metered", "receipt": metered},
        ]
    )
    assert result["complete_cost_advantage"] is None
    assert result["profit_established"] is False
    assert result["fresh_confirmation"] is False
    assert result["production_default_changed"] is False
    with pytest.raises(ValueError, match="paired"):
        scaling.summarize([{"tasks": 4, "mode": "native", "receipt": native}])


def test_original_panel_and_output_paths_are_immutable(tmp_path: Path) -> None:
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(ValueError, match="new regular output"):
        scaling.run(PANEL, SEAL, output, 1)
    scaling.check_seal(PANEL, SEAL)

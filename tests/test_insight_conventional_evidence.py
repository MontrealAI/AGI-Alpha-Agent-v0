# SPDX-License-Identifier: Apache-2.0
"""Keep the conventional challenge bound to its original cases and executable sources."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from alpha_factory_v1.core.runtime.successor.protocol import canonical
from scripts.record_insight_frontier import ROOT, conventional_challenge


def test_challenge_preserves_parity_incomplete_denominator_and_unknown_money() -> None:
    report = conventional_challenge()
    assert report["summary"]["total"] == 24
    assert report["summary"]["exact_execution_parity"] == report["summary"]["complete"] == 23
    assert len(report["summary"]["incomplete_cases"]) == 1
    assert report["technical_breakthrough_claim"] == "stopped"
    assert report["discovery_advantage"] == "untested"
    assert report["money"]["compute_usd"] is None
    assert report["money"]["customer_receipts"] == 0
    assert report["customer_acceptance"] is report["authority_granted"] is False
    assert json.loads(canonical(report)) == report


@pytest.mark.parametrize("damage", ["freeze", "comparator", "candidate", "result-source"])
def test_replaced_challenge_inputs_cannot_qualify_recorded_output(tmp_path: Path, damage: str) -> None:
    names = [
        "evidence/decisive-frontier-20261027/conventional/FREEZE_typecorrected.json",
        "evidence/decisive-frontier-20261027/conventional/RESULT_typecorrected.json",
        "scripts/insight_conventional_challenge.py",
        "alpha_factory_v1/core/runtime/successor/flywheel_access_path.py",
    ]
    for name in names:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    selected = {"freeze": names[0], "comparator": names[2], "candidate": names[3], "result-source": names[1]}[damage]
    path = tmp_path / selected
    if damage == "result-source":
        result = json.loads(path.read_bytes())
        result["source_sha256"] = "0" * 64
        path.write_text(json.dumps(result))
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="conventional"):
        conventional_challenge(tmp_path)

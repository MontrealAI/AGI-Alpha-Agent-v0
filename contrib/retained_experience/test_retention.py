# SPDX-License-Identifier: Apache-2.0
"""Cost-feedback math and actual sealed adverse evidence, with no future claims."""

from __future__ import annotations

import json
import random
import shutil
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.retained_experience import retention
from alpha_factory_v1.core.runtime.retained_experience.experiment import file_hash
from alpha_factory_v1.core.runtime.retained_experience.operator import handle

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "evidence/retained-experience-20261029/prospective-v1"
SEAL = "a1eee42f8701ebceaa53b88d1f59fd15744121317ce1fcb0df1213529295736c"


def test_exact_cost_intersection_preserves_every_comparator() -> None:
    assert retention.eligible_horizons(
        (Fraction(20), Fraction(1)), {"a": (Fraction(0), Fraction(2))}, Fraction(1, 10)
    ) == {
        "minimum": 25,
        "maximum": None,
    }
    controls = {"a": (Fraction(0), Fraction(2)), "b": (Fraction(100), Fraction(1))}
    domain = retention.eligible_horizons((Fraction(20), Fraction(1)), controls, Fraction(1, 10))
    assert domain == {"minimum": 25, "maximum": 700}


def test_declining_advantage_can_have_an_upper_horizon() -> None:
    domain = retention.eligible_horizons(
        (Fraction(0), Fraction(3)), {"a": (Fraction(100), Fraction(2))}, Fraction(1, 10)
    )
    assert domain == {"minimum": 1, "maximum": 75}
    impossible = retention.eligible_horizons(
        (Fraction(10), Fraction(2)), {"a": (Fraction(0), Fraction(2))}, Fraction(1, 10)
    )
    assert impossible == {"minimum": None, "maximum": None}


def test_zero_cost_tie_is_not_a_percentage_improvement() -> None:
    assert retention.eligible_horizons(
        (Fraction(0), Fraction(0)), {"free": (Fraction(0), Fraction(0))}, Fraction(1, 10)
    ) == {
        "minimum": None,
        "maximum": None,
    }


def test_cost_interval_matches_direct_economics_at_switching_boundaries() -> None:
    rng = random.Random(20261029)
    for _ in range(100):
        candidate = (Fraction(rng.randrange(50)), Fraction(rng.randrange(10)))
        controls = {str(i): (Fraction(rng.randrange(50)), Fraction(rng.randrange(10))) for i in range(3)}
        domain = retention.eligible_horizons(candidate, controls, Fraction(1, 10))
        for count in range(1, 100):
            direct = all(
                fixed + count * variable > 0
                and candidate[0] + count * candidate[1] <= Fraction(9, 10) * (fixed + count * variable)
                for fixed, variable in controls.values()
            )
            admitted = (
                domain["minimum"] is not None
                and count >= domain["minimum"]
                and (domain["maximum"] is None or count <= domain["maximum"])
            )
            assert direct == admitted


@pytest.mark.parametrize("count", [0, -1, 1_000_001, True, 1.5])
def test_future_horizons_do_not_grant_unbounded_or_implicit_work(count: Any) -> None:
    with pytest.raises(ValueError, match="future task count"):
        retention.plan(PANEL, SEAL, count)


def test_failed_cost_transfer_becomes_a_constraint_without_changing_evidence() -> None:
    before = file_hash(PANEL / "evidence-seal.json")
    result = retention.plan(PANEL, SEAL, 64)
    assert result["decision"] == "KEEP_INCUMBENT"
    assert result["incumbent"] == "highs-ds-1"
    assert result["historical_result"] == "NOT_DEMONSTRATED"
    assert result["unresolved_historical_costs"]
    assert result["complete_cost_advantage"] is None
    assert result["authority_granted"] is False
    assert result["future_benefit_established"] is False
    assert result["planning_cpu_ns_charged_in_projection"] > 0
    assert file_hash(PANEL / "evidence-seal.json") == before


def test_long_horizon_projection_requires_new_evidence() -> None:
    result = retention.plan(PANEL, SEAL, 100_000)
    scenarios = result["cpu_only_projection_scenarios"]
    assert scenarios["unallocated_verification_fixed"]["meets_frozen_cpu_threshold"] is True
    assert scenarios["unallocated_verification_recurring"]["meets_frozen_cpu_threshold"] is False
    assert result["decision"] == "MEASURE_VERIFICATION_SCALING_FIRST"
    assert result["confirmation"] is False
    assert result["complete_cost_advantage"] is None
    assert result["production_default_changed"] is False


def test_trusted_seal_and_summary_arithmetic_cannot_be_replaced(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="trusted evidence seal"):
        retention.plan(PANEL, "0" * 64, 64)
    destination = tmp_path / "copied"
    shutil.copytree(PANEL, destination)
    summary = json.loads((destination / "summary.json").read_text())
    summary["arms"]["retained"]["setup_cpu_ns"] = 0
    (destination / "summary.json").write_text(json.dumps(summary))
    seal = json.loads((destination / "evidence-seal.json").read_text())
    seal["files"]["summary.json"] = file_hash(destination / "summary.json")
    (destination / "evidence-seal.json").write_text(json.dumps(seal))
    with pytest.raises(ValueError, match="understates historical"):
        retention.plan(destination, file_hash(destination / "evidence-seal.json"), 64)


def test_native_planner_refuses_overwriting_a_prior_lesson(tmp_path: Path) -> None:
    from argparse import Namespace

    output = tmp_path / "lesson.json"
    args = Namespace(
        experience_command="plan-retention", directory=PANEL, seal_sha256=SEAL, future_tasks=64, output=output
    )
    result = handle(args)
    assert result["decision"] == "KEEP_INCUMBENT"
    assert json.loads(output.read_text())["schema"] == retention.SCHEMA
    with pytest.raises(ValueError, match="new retention-plan output"):
        handle(args)

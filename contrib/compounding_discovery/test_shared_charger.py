# SPDX-License-Identifier: Apache-2.0
"""Independent acceptance of a seed-funded joint charging construction."""

from __future__ import annotations

import copy
import argparse
import json
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.compounding_discovery import shared_charger as shared
from alpha_factory_v1.core.runtime.structural_transfer import eadarp, eadarp_check


def public_target() -> dict[str, Any]:
    return json.loads(Path(__file__).with_name("base-target.json").read_text())


def shared_target(rate: str = "2") -> dict[str, Any]:
    base = public_target()
    base["id"] = "development-public-16-passenger-shared-station"
    base["routes"][1] = [44 if node == 42 else node for node in base["routes"][1]]
    base["updates"]["charge_multiplier"] = rate
    return shared.wrap_target(base)


def wrap_artifact(request: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": shared.RESULT_SCHEMA,
        "task_hash": shared.digest(request),
        "status": "FEASIBLE",
        "base_artifact": artifact,
        "resources": {},
        "scope": shared.SCOPE,
    }


def test_original_public_task_has_no_charger_advantage() -> None:
    request = shared.wrap_target(public_target())
    base = request["base_target"]
    ordinary = eadarp.solve_model(base, eadarp.compile_model(base))
    joint = shared.solve(request)
    assert shared.check(request, wrap_artifact(request, ordinary))["accepted"]
    assert shared.check(request, joint)["accepted"]
    assert abs(float(joint["base_artifact"]["objective"]) - float(ordinary["objective"])) < 1e-7


def test_shared_public_route_update_requires_joint_acceptance() -> None:
    request = shared_target()
    base = request["base_target"]
    ordinary = eadarp.solve_model(base, eadarp.compile_model(base))
    assert eadarp_check.check(base, ordinary)["accepted"]
    rejected = shared.check(request, wrap_artifact(request, ordinary))
    assert not rejected["accepted"] and any("shared-port overlap" in reason for reason in rejected["reasons"])
    joint = shared.solve(request)
    checked = shared.check(request, joint)
    assert checked["accepted"]
    assert len(joint["base_artifact"]["vehicles"]) == 2
    assert joint["resources"]["solver_calls"] == 1
    assert joint["resources"]["funding"] == "initial-seed-funded-research"
    assert abs(float(joint["base_artifact"]["objective"]) - float(ordinary["objective"])) < 1e-7
    assert checked["global_optimality_checked"] is False


@pytest.mark.parametrize("rate,scale", [("1.5", "1.5"), ("2", "2"), ("3", "1")])
def test_declared_training_regimes_have_checked_joint_output(rate: str, scale: str) -> None:
    request = shared_target(rate)
    request["base_target"]["updates"]["window_scale"] = scale
    assert shared.check(request, shared.solve(request))["accepted"]


def test_infeasible_search_does_not_forge_a_joint_proof() -> None:
    request = shared_target("1")
    result = shared.solve(request)
    assert result["status"] == "UNRESOLVED"
    assert not shared.check(request, result)["accepted"]


def test_noncolocated_nodes_cannot_be_called_physical_replicas() -> None:
    request = shared_target()
    request["physical_stations"][0]["nodes"].append(43)
    request["physical_stations"] = [group for group in request["physical_stations"] if group["nodes"] != [43]]
    with pytest.raises(ValueError, match="distinct physical locations"):
        shared.solve(request)


def test_complete_station_partition_is_mandatory() -> None:
    request = shared_target()
    request["physical_stations"].pop()
    with pytest.raises(ValueError, match="unmapped raw station"):
        shared.solve(request)


def test_duplicate_station_partition_is_rejected() -> None:
    request = shared_target()
    request["physical_stations"][1]["nodes"] = request["physical_stations"][0]["nodes"]
    with pytest.raises(ValueError, match="exactly once"):
        shared.solve(request)


def test_seed_equity_cannot_be_relabelled_earned_successor() -> None:
    request = shared_target()
    request["funding"] = "earned-successor"
    with pytest.raises(ValueError, match="earned-funding"):
        shared.solve(request)


def test_station_capacity_two_is_not_silently_relaxed() -> None:
    request = shared_target()
    request["physical_stations"][0]["capacity"] = 2
    with pytest.raises(ValueError, match="one physical port"):
        shared.solve(request)


def test_joint_artifact_is_bound_to_exact_wrapper() -> None:
    request = shared_target()
    result = shared.solve(request)
    changed = copy.deepcopy(request)
    changed["id"] += "-changed"
    assert not shared.check(changed, result)["accepted"]


def test_independent_base_equations_still_reject_false_energy() -> None:
    request = shared_target()
    result = shared.solve(request)
    result["base_artifact"]["vehicles"][0]["arrival_kwh"][0] = "100"
    assert not shared.check(request, result)["accepted"]


def test_checker_rebuilds_occupancy_without_trusting_resources() -> None:
    request = shared_target()
    base = request["base_target"]
    ordinary = eadarp.solve_model(base, eadarp.compile_model(base))
    result = wrap_artifact(request, ordinary)
    result["resources"] = {"solver_calls": 0, "claimed_nonoverlap": True}
    assert not shared.check(request, result)["accepted"]


def test_more_than_eight_charger_visits_refuses_before_solver() -> None:
    base = public_target()
    for vehicle, route in enumerate(base["routes"]):
        no_stations = [node for node in route if node not in range(42, 47)]
        base["routes"][vehicle] = no_stations[:-1] + list(range(42, 47)) + no_stations[-1:]
    request = shared.wrap_target(base)
    with pytest.raises(ValueError, match="eight charger visits"):
        shared.solve(request)


def test_command_artifacts_replay_and_cannot_overwrite(tmp_path: Path) -> None:
    source, output = tmp_path / "input.json", tmp_path / "output"
    source.write_text(json.dumps(shared_target()))
    args = argparse.Namespace(action="solve", file=source, output=output)
    assert shared.handle(args)["accepted"]
    assert shared.handle(argparse.Namespace(action="check", file=output, output=None))["accepted"]
    with pytest.raises(FileExistsError):
        shared.handle(args)


def test_command_preserves_failed_seed_attribution(tmp_path: Path) -> None:
    request = shared_target()
    request["funding"] = "fake-earned"
    source, output = tmp_path / "input.json", tmp_path / "failed"
    source.write_text(json.dumps(request))
    with pytest.raises(ValueError):
        shared.handle(argparse.Namespace(action="solve", file=source, output=output))
    assert json.loads((output / "failure.json").read_text())["task_hash"] == shared.digest(request)
    assert not (output / "result.json").exists()

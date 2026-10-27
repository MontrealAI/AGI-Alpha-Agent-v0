# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

TOL = 1e-12


def number(value: Any, maximum: float = math.inf) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("A finite number is required")
    value = float(value)
    if not math.isfinite(value) or value < 0 or value > maximum:
        raise ValueError("Number outside the declared domain")
    return value


def name(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 180:
        raise ValueError("A bounded nonempty identifier is required")
    return value


def vector(value: Any, n: int) -> list[float]:
    if not isinstance(value, list) or len(value) != n:
        raise ValueError("Probability vector dimension mismatch")
    return [number(x, 1) for x in value]


def unique(records: Any, limit: int) -> None:
    if not isinstance(records, list) or not 1 <= len(records) <= limit:
        raise ValueError("Record count outside scope")
    ids = [name(x["id"]) for x in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate identifier")


def validate(mission: dict[str, Any]) -> None:
    if mission.get("schema") != "shared-observation-mission/v1" or mission.get("evidence_type") != "synthetic":
        raise ValueError("Only the declared synthetic research scope is supported")
    name(mission["mission_id"])
    name(mission["calibration_scope"])
    states = mission["states"]
    if not isinstance(states, list) or not 1 <= len(states) <= 12:
        raise ValueError("State count outside scope")
    if len({name(s) for s in states}) != len(states):
        raise ValueError("Duplicate state")
    n = len(states)
    prior = vector(mission["prior"], n)
    if abs(math.fsum(prior) - 1) > TOL:
        raise ValueError("Prior is not normalized")
    obs = mission["observation"]
    name(obs["id"])
    name(obs["calibration_scope"])
    if any(not isinstance(obs[k], bool) for k in ["usable", "rights_cleared"]):
        raise ValueError("Observation prerequisites must be booleans")
    unique(obs["outcomes"], 12)
    for outcome in obs["outcomes"]:
        if outcome["id"] == "__timeout__":
            raise ValueError("Reserved outcome identifier")
        vector(outcome["likelihood"], n)
        if outcome["arrival_hours"] is not None:
            number(outcome["arrival_hours"])
    for state in range(n):
        if abs(math.fsum(o["likelihood"][state] for o in obs["outcomes"]) - 1) > TOL:
            raise ValueError("Observation likelihood columns are not normalized")
    unique(mission["operators"], 6)
    for operator in mission["operators"]:
        number(operator["risk_limit"], 1)
        number(operator["decision_deadline_hours"])
        name(operator["fallback_action"])
        unique(operator["actions"], 6)
        if operator["fallback_action"] not in {a["id"] for a in operator["actions"]}:
            raise ValueError("Fallback action does not exist")
        for action in operator["actions"]:
            vector(action["risk_by_state"], n)
            number(action["cost_usd"])
            number(action["latest_start_hours"])


def risk(action: dict[str, Any], posterior: list[float]) -> float:
    return math.fsum(x * y for x, y in zip(action["risk_by_state"], posterior, strict=True))


def admissible(action: dict[str, Any], posterior: list[float], when: float, limit: float) -> bool:
    return when <= action["latest_start_hours"] + TOL and risk(action, posterior) <= limit + TOL


def choose(operator: dict[str, Any], posterior: list[float], when: float) -> dict[str, Any] | None:
    allowed = [a for a in operator["actions"] if admissible(a, posterior, when, operator["risk_limit"])]
    return min(allowed, key=lambda a: (a["cost_usd"], a["id"])) if allowed else None


def make_branch(operator: dict[str, Any], prior: list[float], branch_id: str, likelihood: list[float],
                when: float, timeout: bool) -> dict[str, Any]:
    masses = [prior_mass * likelihood_mass for prior_mass, likelihood_mass in zip(prior, likelihood, strict=True)]
    probability = math.fsum(masses)
    branch = {"id": branch_id, "probability": probability, "observed_at_hours": when,
              "reachable": probability > 0, "posterior": None, "action": None, "risk": None,
              "cost_usd": None, "valid": None}
    if probability == 0:
        return branch
    posterior = [x / probability for x in masses]
    action = (next(a for a in operator["actions"] if a["id"] == operator["fallback_action"])
              if timeout else choose(operator, posterior, when))
    branch.update(posterior=posterior, valid=False)
    if action is not None:
        branch.update(action=action["id"], risk=risk(action, posterior), cost_usd=action["cost_usd"],
                      valid=admissible(action, posterior, when, operator["risk_limit"]))
    return branch


def compile_mission(mission: dict[str, Any]) -> dict[str, Any]:
    validate(mission)
    prior, obs = mission["prior"], mission["observation"]
    prerequisites = (obs["usable"] and obs["rights_cleared"] and
                     obs["calibration_scope"] == mission["calibration_scope"])
    reports = []
    for operator in mission["operators"]:
        baseline = choose(operator, prior, 0)
        baseline_cost = baseline["cost_usd"] if baseline else None
        branches = []
        if prerequisites:
            late = [0.0] * len(prior)
            for outcome in obs["outcomes"]:
                arrival = outcome["arrival_hours"]
                if arrival is None or arrival > operator["decision_deadline_hours"]:
                    late = [x + y for x, y in zip(late, outcome["likelihood"], strict=True)]
                else:
                    branches.append(make_branch(operator, prior, outcome["id"], outcome["likelihood"], arrival, False))
            branches.append(make_branch(operator, prior, "__timeout__", late,
                                        operator["decision_deadline_hours"], True))
        valid = prerequisites and all(b["valid"] is True for b in branches if b["reachable"])
        if branches and abs(math.fsum(b["probability"] for b in branches) - 1) > TOL:
            raise ValueError("Internal branch probability conservation failed")
        contingent = math.fsum(b["probability"] * b["cost_usd"] for b in branches if b["reachable"]) if valid else None
        reports.append({"id": operator["id"], "baseline_action": baseline["id"] if baseline else None,
                        "baseline_cost": baseline_cost, "baseline_valid": baseline is not None,
                        "contingent_cost": contingent,
                        "value_of_information": baseline_cost - contingent if baseline is not None and valid else None,
                        "valid": valid, "peak_action_reserve": max((b["cost_usd"] or 0 for b in branches), default=0),
                        "branches": branches})
    accepted = prerequisites and all(x["valid"] for x in reports)
    baseline_all = all(x["baseline_valid"] for x in reports)
    return {"schema": "shared-observation-result/v1", "mission_id": mission["mission_id"],
            "evidence_type": "executed_computation_over_synthetic_probabilities",
            "observation_accepted": accepted, "operators": reports,
            "total_baseline_cost": math.fsum(x["baseline_cost"] for x in reports) if baseline_all else None,
            "total_contingent_cost": math.fsum(x["contingent_cost"] for x in reports) if accepted else None,
            "total_value_of_information": math.fsum(x["value_of_information"] for x in reports) if accepted and baseline_all else None,
            "source_of_probabilities": "supplied_synthetic_mission_not_learned_sensor_or_orbital_model",
            "execution_authorized": False}


def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out = {}
    for key, value in items:
        if key in out:
            raise ValueError("Duplicate JSON field")
        out[key] = value
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    try:
        raw = args.mission.read_bytes()
        if len(raw) > 1_000_000:
            raise ValueError("Mission input is too large")
        if args.profile:
            profile = json.loads(args.profile.read_bytes(), object_pairs_hook=pairs)
            if profile.get("schema") != "shared-observation-profile/v1" or profile.get("version") != "1.0.0":
                raise ValueError("Unsupported artifact profile")
        result = compile_mission(json.loads(raw, object_pairs_hook=pairs))
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
        result["compiler_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        return 0
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as error:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"accepted": False, "error": str(error), "execution_authorized": False}) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

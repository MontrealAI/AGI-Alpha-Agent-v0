# SPDX-License-Identifier: Apache-2.0
"""Independent finite-model reference and semantic checker; no flight authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any


TOL = Fraction(1, 10**12)


def q(value: int | float | str) -> Fraction:
    """Interpret supplied decimal values without cumulative float arithmetic."""
    return Fraction(str(value))


def number(value: Any, label: str, upper: int | None = None) -> Fraction:
    """Validate one nonnegative finite numeric field."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}: finite number required")
    result = q(value)
    if result < 0 or (upper is not None and result > upper):
        raise ValueError(f"{label}: numeric range")
    return result


def identifier(value: Any, label: str) -> str:
    """Validate an explicit nonempty identifier."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}: nonempty string required")
    return value


def vector(value: Any, n: int, label: str, normalized: bool = False) -> list[Fraction]:
    """Validate a probability vector with declared dimensionality."""
    if not isinstance(value, list) or len(value) != n:
        raise ValueError(f"{label}: dimension")
    out = [number(x, label, 1) for x in value]
    if normalized and abs(sum(out) - 1) > TOL:
        raise ValueError(f"{label}: normalization")
    return out


def records(value: Any, bound: int, label: str) -> list[dict[str, Any]]:
    """Validate bounded lists of uniquely named records."""
    if not isinstance(value, list) or not 1 <= len(value) <= bound:
        raise ValueError(f"{label}: bounded nonempty list required")
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{label}: object required")
        name = identifier(item.get("id"), label)
        if name in seen:
            raise ValueError(f"{label}: duplicate identifier")
        seen.add(name)
    return value


def validate(mission: dict[str, Any]) -> None:
    """Validate the frozen mission contract independently."""
    if mission.get("schema") != "shared-observation-mission/v1" or mission.get("evidence_type") != "synthetic":
        raise ValueError("mission schema/evidence type")
    identifier(mission.get("mission_id"), "mission_id")
    identifier(mission.get("calibration_scope"), "calibration_scope")
    states = mission.get("states")
    if not isinstance(states, list) or not 1 <= len(states) <= 12:
        raise ValueError("states: bounded nonempty list required")
    names = [identifier(x, "state") for x in states]
    if len(set(names)) != len(names):
        raise ValueError("states: duplicate identifier")
    n = len(states)
    vector(mission.get("prior"), n, "prior", True)
    obs = mission.get("observation")
    if not isinstance(obs, dict):
        raise ValueError("observation: object required")
    identifier(obs.get("id"), "observation.id")
    identifier(obs.get("calibration_scope"), "observation.calibration_scope")
    if not isinstance(obs.get("usable"), bool) or not isinstance(obs.get("rights_cleared"), bool):
        raise ValueError("observation: explicit prerequisite booleans required")
    outcomes = records(obs.get("outcomes"), 12, "outcomes")
    matrix = []
    for out in outcomes:
        if out["id"] == "__timeout__":
            raise ValueError("outcome id '__timeout__' is reserved")
        matrix.append(vector(out.get("likelihood"), n, "outcome.likelihood"))
        if out.get("arrival_hours") is not None:
            number(out["arrival_hours"], "outcome.arrival_hours")
    if any(abs(sum(row[j] for row in matrix) - 1) > TOL for j in range(n)):
        raise ValueError("outcomes: likelihood columns must sum to one")
    for op in records(mission.get("operators"), 6, "operators"):
        number(op.get("risk_limit"), "operator.risk_limit", 1)
        number(op.get("decision_deadline_hours"), "operator.decision_deadline_hours")
        actions = records(op.get("actions"), 6, "actions")
        if op.get("fallback_action") not in {a["id"] for a in actions}:
            raise ValueError("operator: fallback action missing")
        for action in actions:
            vector(action.get("risk_by_state"), n, "action.risk_by_state")
            number(action.get("cost_usd"), "action.cost_usd")
            number(action.get("latest_start_hours"), "action.latest_start_hours")


def risk(action: dict[str, Any], posterior: list[Fraction]) -> Fraction:
    """Compute a branch's conditional risk from supplied finite consequences."""
    return sum((q(a) * p for a, p in zip(action["risk_by_state"], posterior, strict=True)), Fraction())


def cheapest(op: dict[str, Any], posterior: list[Fraction], time: Fraction) -> dict[str, Any] | None:
    """Exhaustively enumerate actions and select the cheapest admissible one."""
    feasible = []
    for action in op["actions"]:
        if time <= q(action["latest_start_hours"]) + TOL and risk(action, posterior) <= q(op["risk_limit"]) + TOL:
            feasible.append(action)
    return min(feasible, key=lambda a: (q(a["cost_usd"]), a["id"]), default=None)


def reference(mission: dict[str, Any], input_sha256: str) -> dict[str, Any]:
    """Enumerate the exact conventional policy without importing the capability."""
    validate(mission)
    prior = [q(x) for x in mission["prior"]]
    n = len(prior)
    obs = mission["observation"]
    prerequisites = obs["usable"] and obs["rights_cleared"] and obs["calibration_scope"] == mission["calibration_scope"]
    operators = []
    for op in mission["operators"]:
        base = cheapest(op, prior, Fraction())
        result: dict[str, Any] = {
            "id": op["id"],
            "baseline_cost": float(q(base["cost_usd"])) if base else None,
            "baseline_action": base["id"] if base else None,
            "contingent_cost": None,
            "value_of_information": None,
            "valid": False,
            "peak_action_reserve": None,
            "branches": [],
        }
        if not prerequisites:
            operators.append(result)
            continue
        deadline = q(op["decision_deadline_hours"])
        branch_specs: list[tuple[str, list[Fraction], Fraction, bool]] = []
        timeout = [Fraction() for _ in range(n)]
        for out in obs["outcomes"]:
            arrival = out["arrival_hours"]
            likelihood = [q(x) for x in out["likelihood"]]
            if arrival is None or q(arrival) > deadline + TOL:
                timeout = [x + y for x, y in zip(timeout, likelihood, strict=True)]
            else:
                branch_specs.append((out["id"], likelihood, q(arrival), False))
        branch_specs.append(("__timeout__", timeout, deadline, True))
        expected = Fraction()
        reserve = Fraction()
        all_valid = True
        for name, likelihood, arrival, is_timeout in branch_specs:
            mass = [p * ell for p, ell in zip(prior, likelihood, strict=True)]
            probability = sum(mass)
            branch: dict[str, Any] = {
                "id": name,
                "probability": float(probability),
                "posterior": None,
                "observed_at_hours": float(arrival),
                "action": None,
                "risk": None,
                "cost_usd": None,
                "valid": None,
                "reachable": probability > 0,
            }
            if probability > 0:
                posterior = [x / probability for x in mass]
                action = (
                    next(a for a in op["actions"] if a["id"] == op["fallback_action"])
                    if is_timeout
                    else cheapest(op, posterior, arrival)
                )
                branch["posterior"] = [float(x) for x in posterior]
                ok = action is not None
                if action is not None:
                    action_risk = risk(action, posterior)
                    ok = action_risk <= q(op["risk_limit"]) + TOL and arrival <= q(action["latest_start_hours"]) + TOL
                    branch.update(action=action["id"], risk=float(action_risk), cost_usd=float(q(action["cost_usd"])))
                    expected += probability * q(action["cost_usd"])
                    reserve = max(reserve, q(action["cost_usd"]))
                branch["valid"] = ok
                all_valid = all_valid and ok
            result["branches"].append(branch)
        result["valid"] = all_valid
        result["peak_action_reserve"] = float(reserve)
        if all_valid:
            result["contingent_cost"] = float(expected)
            if base:
                result["value_of_information"] = float(q(base["cost_usd"]) - expected)
        operators.append(result)
    accepted = prerequisites and all(o["valid"] for o in operators)
    base_total = (
        sum(q(o["baseline_cost"]) for o in operators)
        if all(o["baseline_cost"] is not None for o in operators)
        else None
    )
    contingent_total = sum(q(o["contingent_cost"]) for o in operators) if accepted else None
    return {
        "schema": "shared-observation-result/v1",
        "mission_id": mission["mission_id"],
        "input_sha256": input_sha256,
        "observation_accepted": accepted,
        "operators": operators,
        "total_baseline_cost": float(base_total) if base_total is not None else None,
        "total_contingent_cost": float(contingent_total) if contingent_total is not None else None,
        "total_value_of_information": float(base_total - contingent_total)
        if base_total is not None and contingent_total is not None
        else None,
        "execution_authorized": False,
        "reference_method": "independent finite enumeration with rational arithmetic",
    }


def compatible(left: Any, right: Any, tolerance: float = 1e-9) -> bool:
    """Compare numeric observations without accepting null/boolean substitutions."""
    if isinstance(left, bool) or isinstance(right, bool) or left is None or right is None:
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return (
            math.isfinite(left) and math.isfinite(right) and math.isclose(left, right, abs_tol=tolerance, rel_tol=1e-10)
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(compatible(a, b, tolerance) for a, b in zip(left, right, strict=True))
    return type(left) is type(right) and left == right


def check(mission: dict[str, Any], supplied: dict[str, Any], input_sha256: str) -> dict[str, Any]:
    """Independently inspect decisions, every branch and all claimed totals."""
    expected = reference(mission, input_sha256)
    failures: list[str] = []
    checks = 0

    def compare(a: dict[str, Any], b: dict[str, Any], key: str, path: str, tolerance: float = 1e-9) -> None:
        nonlocal checks
        checks += 1
        if key not in b or not compatible(a[key], b[key], tolerance):
            failures.append(f"{path}.{key}: expected {a[key]!r}, received {b.get(key)!r}")

    for key in [
        "schema",
        "mission_id",
        "input_sha256",
        "execution_authorized",
        "observation_accepted",
        "total_baseline_cost",
        "total_contingent_cost",
        "total_value_of_information",
    ]:
        compare(expected, supplied, key, "result")
    provided_ops = supplied.get("operators", [])
    if not isinstance(provided_ops, list) or any(not isinstance(x, dict) for x in provided_ops):
        provided_ops = []
    actual_ops = {x.get("id"): x for x in provided_ops}
    checks += 1
    if set(actual_ops) != {x["id"] for x in expected["operators"]} or len(actual_ops) != len(provided_ops):
        failures.append("result.operators: missing, unexpected or duplicate operator")
    for op in expected["operators"]:
        actual = actual_ops.get(op["id"], {})
        path = f"operator[{op['id']}]"
        for key in ["baseline_cost", "baseline_action", "contingent_cost", "value_of_information", "valid"]:
            compare(op, actual, key, path)
        if op["valid"]:
            compare(op, actual, "peak_action_reserve", path)
        branches = actual.get("branches", [])
        if not isinstance(branches, list) or any(not isinstance(x, dict) for x in branches):
            branches = []
        indexed = {x.get("id"): x for x in branches}
        checks += 1
        if set(indexed) != {x["id"] for x in op["branches"]} or len(indexed) != len(branches):
            failures.append(f"{path}.branches: missing, unexpected or duplicate branch")
        for branch in op["branches"]:
            other = indexed.get(branch["id"], {})
            for key in [
                "probability",
                "posterior",
                "observed_at_hours",
                "action",
                "risk",
                "cost_usd",
                "valid",
                "reachable",
            ]:
                compare(branch, other, key, f"{path}.branch[{branch['id']}]", 1e-12)
    return {
        "schema": "shared-observation-independent-check/v1",
        "mission_id": mission["mission_id"],
        "input_sha256": input_sha256,
        "conforms_to_independent_reference": not failures,
        "reference_observation_accepted": expected["observation_accepted"],
        "checks": checks,
        "failures": failures,
        "execution_authorized": False,
    }


def load(path: Path) -> tuple[dict[str, Any], str]:
    """Parse JSON and bind the exact supplied bytes."""
    raw = path.read_bytes()
    value = json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"invalid JSON number {x}")))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value, hashlib.sha256(raw).hexdigest()


def main() -> int:
    """Write an independent reference result or inspect a submitted result."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    args = parser.parse_args()
    try:
        mission, digest = load(args.mission)
        result = check(mission, load(args.candidate)[0], digest) if args.candidate else reference(mission, digest)
        code = 0 if result.get("conforms_to_independent_reference", True) else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"schema": "shared-observation-error/v1", "error": str(exc), "execution_authorized": False}
        code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

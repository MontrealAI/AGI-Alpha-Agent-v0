# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..structural_transfer.contracts import bounded, digest, exact_keys

FIELDS = {
    "available": "microUSD",
    "price": "microUSD",
    "production": "microUSD",
    "measured_value": "microUSD",
    "required_value": "microUSD",
    "measurement_valid": "boolean",
}
ACTIONS = {"screen", "measure", "fund", "produce", "inspect", "settle"}


def field(name: str) -> dict[str, Any]:
    return {"op": "field", "name": name, "unit": FIELDS[name]}


def sufficient(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {"op": "ge", "left": left, "right": right}


def expression(node: dict[str, Any], frame: dict[str, Any] | None = None, depth: int = 0) -> tuple[str, Any]:
    if depth > 8:
        raise ValueError("expression depth cap")
    if node.get("op") == "field":
        exact_keys(node, {"op", "name", "unit"})
        if node["name"] not in FIELDS or FIELDS[node["name"]] != node["unit"]:
            raise ValueError("unknown field or unit")
        if frame is None:
            return node["unit"], None
        if node["name"] not in frame:
            raise ValueError("observation unavailable; measurement must precede use")
        return node["unit"], frame[node["name"]]
    exact_keys(node, {"op", "left", "right"})
    if node["op"] not in {"add", "ge"}:
        raise ValueError("unsupported expression")
    lu, lv = expression(node["left"], frame, depth + 1)
    ru, rv = expression(node["right"], frame, depth + 1)
    if lu != ru or lu == "boolean":
        raise ValueError("incompatible arithmetic units")
    unit = "boolean" if node["op"] == "ge" else lu
    return unit, None if frame is None else (lv >= rv if node["op"] == "ge" else lv + rv)


def validate(program: dict[str, Any]) -> None:
    bounded(program)
    exact_keys(program, {"schema", "steps"})
    if program["schema"] != "agialpha/contingent-strategy/v1":
        raise ValueError("strategy version")
    if not isinstance(program["steps"], list) or not 1 <= len(program["steps"]) <= 32:
        raise ValueError("strategy step cap")
    for node in program["steps"]:
        if node.get("op") == "guard":
            exact_keys(node, {"op", "test", "constraint"})
            if node["constraint"] not in {
                "measurement-before-production",
                "collateral-and-production",
                "paid-production",
            }:
                raise ValueError("uninstalled constraint family")
            if expression(node["test"])[0] != "boolean":
                raise ValueError("guard requires boolean")
        else:
            exact_keys(node, {"op"})
            if node["op"] not in ACTIONS:
                raise ValueError("uninstalled action; no shell, network or hardware operator")
    ops = [x["op"] for x in program["steps"] if x["op"] != "guard"]
    if len(ops) != len(set(ops)) or set(ops) != ACTIONS or ops[0] != "screen":
        raise ValueError("exactly one complete service lifecycle required")
    if not ops.index("fund") < ops.index("inspect") < ops.index("settle"):
        raise ValueError("fund/inspection/settlement ordering")
    if not ops.index("produce") < ops.index("inspect"):
        raise ValueError("inspection requires constructed output")


def initial_program() -> dict[str, Any]:
    return {
        "schema": "agialpha/contingent-strategy/v1",
        "steps": [{"op": op} for op in ["screen", "fund", "produce", "measure", "inspect", "settle"]],
    }


def adapt(program: dict[str, Any], constraint: dict[str, Any]) -> dict[str, Any]:
    validate(program)
    if constraint.get("validated") is not True or constraint.get("candidate_hash") != digest(program):
        raise ValueError("constraint must bind a reproduced failure of this candidate")
    out = deepcopy(program)
    steps = out["steps"]
    family = constraint.get("family")
    if family == "measurement-before-production":
        steps.remove({"op": "measure"})
        index = next(i for i, x in enumerate(steps) if x["op"] == "fund")
        steps[index:index] = [
            {"op": "measure"},
            {"op": "guard", "test": field("measurement_valid"), "constraint": family},
            {"op": "guard", "test": sufficient(field("measured_value"), field("required_value")), "constraint": family},
        ]
    elif family == "collateral-and-production":
        index = next(i for i, x in enumerate(steps) if x["op"] == "fund")
        steps.insert(
            index,
            {
                "op": "guard",
                "test": sufficient(
                    field("available"), {"op": "add", "left": field("price"), "right": field("production")}
                ),
                "constraint": family,
            },
        )
        index = next(i for i, x in enumerate(steps) if x["op"] == "produce")
        steps.insert(
            index,
            {
                "op": "guard",
                "test": sufficient(field("available"), field("production")),
                "constraint": "paid-production",
            },
        )
    else:
        raise ValueError("unsupported or irrelevant criticism")
    validate(out)
    if digest(out) == digest(program):
        raise ValueError("adaptation did not change executable behavior")
    return out

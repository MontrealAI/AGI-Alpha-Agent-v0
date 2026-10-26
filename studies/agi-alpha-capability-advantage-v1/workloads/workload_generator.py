"""Construct separately owned public tasks and answer-side numerical records."""

from __future__ import annotations

import hashlib
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

SCHEMA = "agi-alpha-conductance-job/v1"
FAMILIES = ("forward", "inverse", "design")
PROFILES = (
    {"name": "grid", "side": 10, "loads": 4, "parameters": 4, "design_edges": 8},
    {"name": "anisotropic-grid", "side": 25, "loads": 8, "parameters": 12, "design_edges": 24},
    {"name": "irregular-connected", "side": 40, "loads": 12, "parameters": 20, "design_edges": 48},
    {"name": "long-range-grid", "side": 50, "loads": 16, "parameters": 32, "design_edges": 80},
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _operator(network: dict[str, Any], coefficients: np.ndarray) -> sparse.csr_matrix:
    size = network["node_count"]
    rows: list[int] = []
    cols: list[int] = []
    values: list[float] = []
    for (u, v, _), coefficient in zip(network["edges"], coefficients):
        rows.extend((u, v, u, v))
        cols.extend((u, v, v, u))
        values.extend((coefficient, coefficient, -coefficient, -coefficient))
    rows.extend(range(size))
    cols.extend(range(size))
    values.extend(network["ground"])
    return sparse.coo_matrix((values, (rows, cols)), shape=(size, size)).tocsr()


def build_case(family: str, seed: int, profile: dict[str, Any], split: str, identifier: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if family not in FAMILIES:
        raise ValueError("unsupported family")
    rng = np.random.default_rng(seed)
    side = int(profile["side"])
    size = side * side
    pairs: list[tuple[int, int]] = []
    for row in range(side):
        for col in range(side):
            node = row * side + col
            if col + 1 < side:
                pairs.append((node, node + 1))
            if row + 1 < side:
                pairs.append((node, node + side))
    name = profile["name"]
    if name in ("irregular-connected", "long-range-grid"):
        extra = side if name == "irregular-connected" else size // 3
        present = set(pairs)
        while extra:
            u, v = sorted(rng.choice(size, 2, replace=False).tolist())
            if (u, v) not in present:
                pairs.append((u, v))
                present.add((u, v))
                extra -= 1
    coefficients = rng.uniform(0.55, 1.8, len(pairs))
    if name == "anisotropic-grid":
        coefficients *= np.array([0.12 if v == u + side else 2.5 for u, v in pairs])
    ground = np.full(size, 0.015)
    ground[0] = 1.0
    ground[-1] = 0.7
    network = {"node_count": size, "edges": [[int(u), int(v), float(c)] for (u, v), c in zip(pairs, coefficients)], "ground": ground.tolist()}
    count = int(profile["loads"])
    loads = rng.normal(0, 0.25, (count, size))
    for index, load in enumerate(loads):
        load[index * max(1, size // count)] += 2.0
        load[-1 - index * max(1, size // count)] -= 1.5
    task: dict[str, Any] = {"schema": SCHEMA, "id": identifier, "family": family, "split": split, "profile": name, "network": network, "loads": loads.tolist(), "provenance": {"data_class": "synthetic-research", "customer_demand": "unobserved", "physical_validation": "not-run"}}
    oracle: dict[str, Any] = {"task_id": identifier, "seed": int(seed), "scope": "same-session-independent-numerical-acceptance"}
    if family == "forward":
        operator = _operator(network, coefficients)
        states = spsolve(operator, loads.T).T
        oracle["states"] = states.tolist()
    elif family == "inverse":
        parameter_count = int(profile["parameters"])
        order = rng.permutation(len(pairs))
        groups = [sorted(x.tolist()) for x in np.array_split(order, parameter_count)]
        bounds = [[0.5, 2.0] for _ in groups]
        truth = rng.uniform(0.7, 1.7, parameter_count)
        changed = coefficients.copy()
        for group, multiplier in zip(groups, truth):
            changed[group] *= multiplier
        operator = _operator(network, changed)
        states = spsolve(operator, loads.T).T
        sensors = sorted(rng.choice(size, max(12, size // 3), replace=False).tolist())
        prediction_loads = rng.normal(0, 0.3, (3, size))
        prediction_states = spsolve(operator, prediction_loads.T).T
        task["parameters"] = {"groups": groups, "bounds": bounds, "initial": [1.0] * parameter_count}
        task["observations"] = {"nodes": sensors, "states": states[:, sensors].tolist(), "noise_model": "exact-synthetic-state-observations"}
        task["prediction_loads"] = prediction_loads.tolist()
        oracle.update({"parameters": truth.tolist(), "states": states.tolist(), "prediction_states": prediction_states.tolist()})
    else:
        selected = sorted(rng.choice(len(pairs), int(profile["design_edges"]), replace=False).tolist())
        upper = rng.uniform(0.7, 1.8, len(selected))
        costs = rng.uniform(0.8, 1.2, len(selected))
        task["design"] = {"edge_indices": selected, "upper_bounds": upper.tolist(), "costs": costs.tolist(), "resource_budget": float(0.38 * np.dot(upper, costs)), "objective": "minimize-maximum-scenario-compliance"}
    oracle["task_sha256"] = hashlib.sha256(canonical(task)).hexdigest()
    return task, oracle


def save_case(root: Path, task: dict[str, Any], oracle: dict[str, Any]) -> None:
    public = root / "tasks" / (task["id"] + ".json")
    hidden = root / "oracles" / (task["id"] + ".json")
    public.parent.mkdir(parents=True, exist_ok=True)
    hidden.parent.mkdir(parents=True, exist_ok=True)
    public.write_bytes(canonical(task) + b"\n")
    hidden.write_bytes(canonical(oracle) + b"\n")


def build_chain(seed: int, profile: dict[str, Any], split: str, chain_id: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    chain = [build_case(family, seed, profile, split, chain_id + "-" + family.upper()) for family in FAMILIES]
    for index, (task, oracle) in enumerate(chain):
        task["lineage"] = {"chain_id": chain_id, "generation": index + 1, "predecessor_task_id": None if index == 0 else chain[index - 1][0]["id"]}
        oracle["task_sha256"] = hashlib.sha256(canonical(task)).hexdigest()
    inverse_task, inverse_oracle = chain[1]
    design_task, design_oracle = chain[2]
    truth_network = deepcopy(inverse_task["network"])
    for group, multiplier in zip(inverse_task["parameters"]["groups"], inverse_oracle["parameters"]):
        for edge_index in group:
            truth_network["edges"][edge_index][2] *= multiplier
    design_oracle.update({"template_network": deepcopy(design_task["network"]), "true_calibrated_network": truth_network, "predecessor_task_sha256": inverse_oracle["task_sha256"], "design_source_rule": "must-materialize-from-accepted-actual-inverse-output-before-solving"})
    return chain


def materialize_design(template: dict[str, Any], inverse_task: dict[str, Any], inverse_result: dict[str, Any], inverse_acceptance: dict[str, Any]) -> dict[str, Any]:
    if not inverse_acceptance.get("accepted") or inverse_result.get("status") != "complete":
        raise ValueError("upstream inverse outcome is not independently accepted")
    if template["family"] != "design" or inverse_task["family"] != "inverse" or template["lineage"]["predecessor_task_id"] != inverse_task["id"]:
        raise ValueError("connected chain mismatch")
    parameters = np.asarray(inverse_result["parameters"], dtype=float)
    if parameters.shape != (len(inverse_task["parameters"]["groups"]),) or not np.isfinite(parameters).all():
        raise ValueError("invalid inherited parameters")
    task = deepcopy(template)
    if task["network"] != inverse_task["network"]:
        raise ValueError("template and inverse topology identity mismatch")
    for group, multiplier in zip(inverse_task["parameters"]["groups"], parameters):
        for edge_index in group:
            task["network"]["edges"][edge_index][2] *= float(multiplier)
    task["lineage"]["materialization"] = {"template_sha256": hashlib.sha256(canonical(template)).hexdigest(), "parent_task_sha256": hashlib.sha256(canonical(inverse_task)).hexdigest(), "parent_result_sha256": hashlib.sha256(canonical(inverse_result)).hexdigest(), "parent_acceptance_sha256": hashlib.sha256(canonical(inverse_acceptance)).hexdigest(), "inherited_parameters": parameters.tolist()}
    return task


def generate_primary(destination: Path, freeze_file: Path, freeze_sha256: str) -> dict[str, Any]:
    if destination.exists():
        raise ValueError("primary destination already exists; preserve original corpus")
    freeze_bytes = freeze_file.read_bytes()
    if len(freeze_sha256) != 64 or hashlib.sha256(freeze_bytes).hexdigest() != freeze_sha256:
        raise ValueError("production freeze identity mismatch")
    source = Path(__file__).resolve().parent
    seed_path = source / "sealed" / "primary-seeds.json"
    commitment = json.loads((source / "seed-commitment.json").read_text())
    if hashlib.sha256(seed_path.read_bytes()).hexdigest() != commitment["sha256"]:
        raise ValueError("primary seed commitment mismatch")
    seeds = json.loads(seed_path.read_text())["primary_chain_seeds"]
    if len(seeds) != 12 or len(set(seeds)) != 12:
        raise ValueError("primary seed census")
    destination.mkdir(parents=True)
    chains = []
    for index, seed in enumerate(seeds):
        profile = PROFILES[index // 3]
        identifier = f"P{index + 1:02d}"
        chain = build_chain(seed, profile, "primary", identifier)
        for task, oracle in chain:
            lane = destination / ("sealed-design" if task["family"] == "design" else "forward-inverse")
            save_case(lane, task, oracle)
        chains.append({"chain_id": identifier, "profile": dict(profile), "tasks": [task["id"] for task, _ in chain]})
    files = []
    for path in sorted(destination.rglob("*.json")):
        data = path.read_bytes()
        files.append({"path": str(path.relative_to(destination)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    receipt = {"schema": "capability-advantage-primary-corpus/v1", "source_freeze_sha256": freeze_sha256, "seed_plan_sha256": commitment["sha256"], "chains": chains, "chain_count": 12, "stage_count": 36, "arm_stage_maximum": 144, "statistical_unit": "complete chain", "files": files, "design_release": "held until all 48 inverse arm outcomes are sealed", "case_replacement_allowed": False}
    (destination / "cohort-manifest.json").write_bytes(canonical(receipt) + b"\n")
    return receipt


def release_design(primary_root: Path, inverse_seal_file: Path, inverse_seal_sha256: str) -> dict[str, Any]:
    data = inverse_seal_file.read_bytes()
    if len(inverse_seal_sha256) != 64 or hashlib.sha256(data).hexdigest() != inverse_seal_sha256:
        raise ValueError("inverse outcome seal identity mismatch")
    seal = json.loads(data)
    records = seal["inverse_outcomes"]
    required = {(f"P{number:02d}-INVERSE", arm) for number in range(1, 13) for arm in ("A", "B", "C", "D")}
    seen = set()
    for record in records:
        key = (record["task_id"], record["arm"])
        if key in seen or key not in required:
            raise ValueError("duplicate or undeclared inverse outcome")
        seen.add(key)
        path = Path(record["result_path"])
        if not path.is_absolute():
            path = inverse_seal_file.parent / path
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError("sealed inverse outcome changed")
    if seen != required:
        raise ValueError("all 48 inverse arm outcomes must be sealed, including failures and blocks")
    destination = primary_root / "design-released"
    if destination.exists():
        raise ValueError("design release already exists")
    shutil.copytree(primary_root / "sealed-design", destination)
    receipt = {"schema": "capability-advantage-design-release/v1", "inverse_seal_sha256": inverse_seal_sha256, "sealed_inverse_outcomes": len(records), "design_source": "frozen templates; materialize using each accepted actual parent output", "truth_substitution_allowed": False}
    (primary_root / "design-release.json").write_bytes(canonical(receipt) + b"\n")
    return receipt


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--development", type=Path)
    parser.add_argument("--generate-primary", type=Path)
    parser.add_argument("--source-freeze", type=Path)
    parser.add_argument("--freeze-sha256")
    parser.add_argument("--release-design", type=Path)
    parser.add_argument("--inverse-seal", type=Path)
    parser.add_argument("--inverse-seal-sha256")
    args = parser.parse_args()
    if sum(value is not None for value in (args.development, args.generate_primary, args.release_design)) != 1:
        parser.error("Choose exactly one generation/release operation")
    if args.generate_primary is not None:
        if args.source_freeze is None or args.freeze_sha256 is None:
            parser.error("Primary generation requires --source-freeze and --freeze-sha256")
        receipt = generate_primary(args.generate_primary, args.source_freeze, args.freeze_sha256)
        print(json.dumps({"chain_count": receipt["chain_count"], "stage_count": receipt["stage_count"], "source_freeze_sha256": receipt["source_freeze_sha256"]}))
    elif args.release_design is not None:
        if args.inverse_seal is None or args.inverse_seal_sha256 is None:
            parser.error("Design release requires exact inverse outcome seal")
        print(json.dumps(release_design(args.release_design, args.inverse_seal, args.inverse_seal_sha256)))
    else:
        profile = {"name": "grid", "side": 7, "loads": 3, "parameters": 3, "design_edges": 6}
        for index, family in enumerate(FAMILIES):
            task, oracle = build_case(family, 81001 + index, profile, "development", "DEV-" + family.upper())
            save_case(args.development, task, oracle)

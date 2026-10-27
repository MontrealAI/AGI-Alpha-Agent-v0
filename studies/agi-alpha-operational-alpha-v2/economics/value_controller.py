# SPDX-License-Identifier: Apache-2.0
"""Additive prospective value-of-assessment controller using immutable prior code."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import statistics
from pathlib import Path
from typing import Any, cast

HERE = Path(__file__).resolve().parent
OPTIONAL = ("private_retention", "shared_retention", "library_retention")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))


def dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def original() -> Any:
    protocol = read(HERE / "value_protocol.json")
    if sha(HERE / "run_economics.py") != protocol["unchanged_original_source_sha256"]:
        raise ValueError("original simulator changed")
    if sha(HERE / "protocol.json") != protocol["unchanged_original_protocol_sha256"]:
        raise ValueError("original protocol changed")
    spec = importlib.util.spec_from_file_location("immutable_original_economics", HERE / "run_economics.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("original source missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute(
    module: Any,
    pilot: dict[str, Any],
    config: dict[str, Any],
    seed: int,
    profile: str,
    requested: str,
    selected: dict[str, Any],
    record: bool = False,
) -> dict[str, Any]:
    mode = selected["mode"]
    if requested not in OPTIONAL and mode != "control":
        raise ValueError("control configuration cannot be relabeled as a hold policy")
    if requested in OPTIONAL and mode not in ("hold", "assess"):
        raise ValueError("optional policy needs explicit hold or assess")
    operative = "expert_E" if mode == "hold" else requested
    choice = {"price_ratio": selected["price_ratio"], "reserve_days": selected["reserve_days"]}
    row = cast(dict[str, Any], module.simulate(pilot, config, seed, profile, operative, choice, record=record))
    row.update(policy=requested, requested_policy=requested, operative_policy=operative, controller_mode=mode)
    return row


def bindings() -> dict[str, str]:
    names = [
        "value_controller.py",
        "value_protocol.json",
        "run_economics.py",
        "protocol.json",
        "results/FREEZE.json",
        "results/pilot_input.json",
        "results/confirmation.json",
    ]
    values = {name: sha(HERE / name) for name in names}
    values["../integration/admission.py"] = sha(HERE.parent / "integration/admission.py")
    return values


def freeze(out: Path) -> None:
    if (out / "VALUE_FREEZE.json").exists():
        raise ValueError("refusing to overwrite value-controller freeze")
    module = original()
    protocol = read(HERE / "value_protocol.json")
    config = read(HERE / "protocol.json")
    pilot = module.load_pilot(HERE / "results/pilot_input.json")
    selection: dict[str, Any] = {}
    development = []
    for policy in module.POLICIES:
        candidates = []
        for mode in protocol["modes"] if policy in OPTIONAL else ["control"]:
            for ratio in config["price_ratios"]:
                for reserve in config["reserve_days_grid"]:
                    selected = {"mode": mode, "price_ratio": ratio, "reserve_days": reserve}
                    rows = [
                        execute(module, pilot, config, seed, "reference", policy, selected)
                        for seed in range(config["development_seeds"][0], config["development_seeds"][1] + 1)
                    ]
                    profits = [float(row["profit_cents"]) for row in rows]
                    score = 0.5 * statistics.mean(profits) + 0.5 * module.quantile(profits, 0.1)
                    candidates.append((score, mode == "hold", -ratio, -reserve, selected))
                    development.append(
                        {
                            "policy": policy,
                            "selected": selected,
                            "objective_cents": score,
                            "run_summaries": [{k: v for k, v in row.items() if k != "events"} for row in rows],
                        }
                    )
        selection[policy] = max(candidates, key=lambda x: x[:4])[4]
    if selection["shared_retention"] != selection["library_retention"]:
        raise AssertionError("same-content library selection differs")
    out.mkdir(parents=True, exist_ok=True)
    (out / "development.json.gz").write_bytes(gzip.compress(json.dumps(development, sort_keys=True).encode(), mtime=0))
    dump(
        out / "VALUE_FREEZE.json",
        {
            "schema": protocol["schema"],
            "bindings": bindings(),
            "selection": selection,
            "development_candidates": len(development),
            "development_histories": sum(len(x["run_summaries"]) for x in development),
            "design_status": protocol["design_status"],
            "confirmation_has_run": False,
        },
    )
    print(json.dumps({"freeze_sha256": sha(out / "VALUE_FREEZE.json"), "selection": selection}, indent=2))


def summary(module: Any, rows: list[dict[str, Any]]) -> dict[str, Any]:
    current = [row for row in rows if row["controller"] == "value_selected"]
    old = [row for row in rows if row["controller"] == "original_selected"]
    result = {
        "value_selected": module.aggregate(current),
        "original_selected_on_same_fresh_worlds": module.aggregate(old),
    }
    keyed = {(r["profile"], r["seed"], r["policy"], r["controller"]): r for r in rows}
    comparisons = {}
    for profile in sorted({row["profile"] for row in rows}):
        seeds = sorted({row["seed"] for row in current if row["profile"] == profile})
        for policy in module.POLICIES:
            pairs = [
                (
                    keyed[profile, seed, policy, "value_selected"]["profit_cents"]
                    - keyed[profile, seed, policy, "original_selected"]["profit_cents"]
                )
                / 100
                for seed in seeds
            ]
            mean = statistics.mean(pairs)
            se = statistics.stdev(pairs) / math.sqrt(len(pairs))
            comparisons[profile + "/" + policy] = {
                "paired_worlds": len(pairs),
                "mean_increment_usd": mean,
                "conditional_monte_carlo_95_interval_usd": [mean - 1.96 * se, mean + 1.96 * se],
                "equal_worlds": sum(v == 0 for v in pairs),
                "positive_worlds": sum(v > 0 for v in pairs),
                "negative_worlds": sum(v < 0 for v in pairs),
            }
    result["value_minus_original_same_fresh_worlds"] = comparisons
    return result


def confirm(out: Path) -> None:
    frozen = read(out / "VALUE_FREEZE.json")
    if frozen["bindings"] != bindings():
        raise ValueError("frozen wrapper, original source/data or protocol changed")
    if (out / "confirmation.json").exists() or (out / "events.jsonl.gz").exists():
        raise ValueError("refusing to overwrite value confirmation")
    module = original()
    protocol = read(HERE / "value_protocol.json")
    config = read(HERE / "protocol.json")
    pilot = module.load_pilot(HERE / "results/pilot_input.json")
    old_freeze = read(HERE / "results/FREEZE.json")
    rows = []
    event_count = 0
    with (out / "events.jsonl.gz").open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as stream:
            for profile in protocol["primary_profiles"] + protocol["stress_profiles"]:
                seeds = (
                    protocol["primary_seeds"] if profile in protocol["primary_profiles"] else protocol["stress_seeds"]
                )
                for seed in range(seeds[0], seeds[1] + 1):
                    for policy in module.POLICIES:
                        for controller in ("value_selected", "original_selected"):
                            if controller == "value_selected":
                                row = execute(
                                    module, pilot, config, seed, profile, policy, frozen["selection"][policy], True
                                )
                            else:
                                row = module.simulate(
                                    pilot, config, seed, profile, policy, old_freeze["selection"][policy], record=True
                                )
                                row.update(
                                    requested_policy=policy,
                                    operative_policy=policy,
                                    controller_mode="assess" if policy in OPTIONAL else "control",
                                )
                            row["controller"] = controller
                            for event in row.pop("events"):
                                data = {
                                    "seed": seed,
                                    "profile": profile,
                                    "policy": policy,
                                    "controller": controller,
                                    "operative_policy": row["operative_policy"],
                                    **event,
                                }
                                stream.write((json.dumps(data, sort_keys=True) + "\n").encode())
                                event_count += 1
                            rows.append(row)
    dump(out / "confirmation.json", rows)
    dump(out / "summary.json", summary(module, rows))
    dump(
        out / "VALUE_CONFIRMATION_COMPLETE.json",
        {
            "freeze_sha256": sha(out / "VALUE_FREEZE.json"),
            "histories": len(rows),
            "events": event_count,
            "confirmation_sha256": sha(out / "confirmation.json"),
            "events_sha256": sha(out / "events.jsonl.gz"),
            "original_results_sha256_unchanged": sha(HERE / "results/confirmation.json"),
            "actual_collections": 0,
            "actual_complete_cost": None,
        },
    )
    print(json.dumps({"histories": len(rows), "events": event_count, "summary": str(out / "summary.json")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "confirm"])
    parser.add_argument("--out", type=Path, default=HERE / "value_results")
    args = parser.parse_args()
    (freeze if args.action == "freeze" else confirm)(args.out)


if __name__ == "__main__":
    main()

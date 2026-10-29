# SPDX-License-Identifier: Apache-2.0
"""Separate, read-only assessment; imports neither progressive runner nor solver."""

from __future__ import annotations

import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
from typing import Any

from alpha_factory_v1.core.runtime.retained_experience import verifier

ROOT = Path(__file__).resolve().parents[2]
STAGES = (0, 4, 8, 12)
METHODS = tuple(f"{method}-{p}" for method in ("highs", "highs-ds", "highs-ipm") for p in (1, 0))
ARMS = (*METHODS, "template", "ordinary-cache", "warm-start", "reset", "frozen", "retained")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def target_from(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    require(set(patch) == {"id", "routes", "updates"}, "target patch changed assumptions or instance")
    return {**deepcopy(base), **deepcopy(patch)}


def memory_check(memory: dict[str, Any], history: list[dict[str, Any]], *, ordinary: bool = False) -> None:
    require(
        memory["memory_hash"] == verifier.hash_value({k: v for k, v in memory.items() if k != "memory_hash"}),
        "memory hash differs",
    )
    require(memory["training"] == [verifier.hash_value(r["target"]) for r in history], "memory lineage differs")
    if not history:
        require(memory["assets"] == [] and memory["failed_constructions"] == [], "zero-history asset leakage")
    elif ordinary:
        known = {verifier.hash_value(r["target"]): r for r in history}
        for asset in memory["assets"]:
            require(
                asset["kind"] == "basis"
                and asset["source"] in known
                and asset["inverse"] == []
                and asset["rows"] == [],
                "ordinary cache gained a learned inverse",
            )
            original = known[asset["source"]]["output"]
            schedule = original["artifact"]["vehicles"][asset["vehicle"]]
            expected = [Decimal(x) for k in ("start_min", "charge_min", "arrival_kwh") for x in schedule[k]]
            require([Decimal(x) for x in asset["point"]] == expected, "ordinary point differs")
            require(asset["duals"] == original["duals"][asset["vehicle"]], "ordinary dual differs")
    else:
        verifier.check_memory(memory, history)


def verify(directory: Path, freeze_sha: str) -> dict[str, Any]:
    require(
        hashlib.sha256((directory / "freeze.json").read_bytes()).hexdigest() == freeze_sha, "trusted freeze differs"
    )
    freeze = verifier.read(directory / "freeze.json")
    for name, digest in freeze["sources"].items():
        p = ROOT / name
        require(
            not Path(name).is_absolute() and ".." not in Path(name).parts and not p.is_symlink(), "unsafe source path"
        )
        require(hashlib.sha256(p.read_bytes()).hexdigest() == digest, "frozen source changed")
        require(
            hashlib.sha256((directory / "source-snapshot" / name).read_bytes()).hexdigest() == digest,
            "frozen source snapshot changed",
        )
    protocol, base = verifier.read(directory / "protocol.json"), verifier.read(directory / "base.json")
    require(
        verifier.hash_value(protocol) == freeze["policy_hash"] and verifier.hash_value(base) == freeze["base_hash"],
        "policy/base changed",
    )
    require(
        protocol["stages"] == list(STAGES)
        and protocol["arms"] == list(ARMS)
        and protocol["repeats"] == 1
        and protocol["cases_per_regime_per_family"] == 2
        and protocol["quality_loss_allowed"] == 0,
        "frozen denominator differs",
    )
    candidate = verifier.read(directory / "candidate-freeze.json")
    for file in ("history", "states"):
        require(
            hashlib.sha256((directory / f"{file}.json").read_bytes()).hexdigest() == candidate[f"{file}_sha256"],
            "candidate changed after freeze",
        )
    require(
        freeze["frozen_at_ns"]
        <= candidate["frozen_at_ns"]
        <= verifier.read(directory / "seed.json")["generated_at_ns"],
        "freeze order differs",
    )
    history = [
        {"target": target_from(base, r["target"]), "output": r["output"]}
        for r in verifier.read(directory / "history.json")
    ]
    require(
        len(history) == 12 and all(r["target"]["routes"] == base["routes"] for r in history), "training family leakage"
    )
    known = {verifier.fingerprint(r["target"]) for r in history}
    require(len(known) == 12, "duplicate training")
    history_cpu = {}
    for stage in STAGES:
        started = time.process_time_ns()
        for row in history[:stage]:
            require(
                verifier.check_output(row["target"], row["output"])["accepted"] is True, "unverified historical output"
            )
        history_cpu[str(stage)] = time.process_time_ns() - started
    states = verifier.read(directory / "states.json")
    require([s["stage"] for s in states] == list(STAGES), "missing or duplicate stage")
    memory_cpu = {}
    for state in states:
        stage = state["stage"]
        require(
            set(state["setup_cpu_ns"]) == set(ARMS)
            and all(type(x) is int and x >= 0 for x in state["setup_cpu_ns"].values()),
            "invalid setup accounting",
        )
        for arm in ARMS:
            started = time.process_time_ns()
            if arm in ("retained", "reset"):
                memory_check(state["memory"], history[:stage])
            elif arm == "ordinary-cache":
                memory_check(state["ordinary"], history[:stage], ordinary=True)
            elif arm == "frozen":
                memory_check(state["frozen"], history[: min(stage, 4)])
            memory_cpu[f"{stage}/{arm}"] = time.process_time_ns() - started
    tasks = verifier.read(directory / "tasks.json")
    require(len(tasks) == 64, "planned task count differs")
    cases: dict[str, tuple[int, str, dict[str, Any]]] = {}
    counts: dict[tuple[int, str], int] = {}
    for row in tasks:
        require(row["stage"] in STAGES and row["family"] in ("same-route", "withheld-stops"), "unknown stage/family")
        target = target_from(base, row["target"])
        routes = deepcopy(base["routes"])
        if row["family"] == "withheld-stops":
            routes[0] = [43 if x == 44 else x for x in routes[0]]
            routes[1] = [46 if x == 42 else x for x in routes[1]]
        require(target["routes"] == routes, "evaluation family differs")
        identity = verifier.fingerprint(target)
        require(identity not in known, "training/evaluation task content repeated")
        known.add(identity)
        cases[verifier.hash_value(target)] = (row["stage"], row["family"], target)
        case_key = row["stage"], row["family"]
        counts[case_key] = counts.get(case_key, 0) + 1
    require(
        all(counts.get((s, f)) == 8 for s in STAGES for f in ("same-route", "withheld-stops")),
        "unequal stage/family denominator",
    )
    seen, rejected = set(), []
    statuses: dict[str, set[str]] = {}
    cpu: dict[str, int] = {}
    accepted_statuses: dict[str, int] = {}
    for line in (directory / "observations.jsonl").read_text().splitlines():
        row = json.loads(line, object_pairs_hook=verifier._pairs)
        key = row["stage"], row["task_hash"], row["arm"]
        require(
            key not in seen and row["arm"] in ARMS and row["task_hash"] in cases, "unknown or duplicate observation"
        )
        stage, family, target = cases[row["task_hash"]]
        require((row["stage"], row["family"]) == (stage, family), "misattributed observation")
        seen.add(key)
        started = time.process_time_ns()
        verdict = (
            verifier.check_output(target, row["output"])
            if "output" in row
            else {"accepted": False, "reason": row.get("failure")}
        )
        if verdict.get("accepted") is not True:
            rejected.append({"key": key, "verdict": verdict})
        else:
            statuses.setdefault(row["task_hash"], set()).add(verdict["status"])
            status_key = f"{stage}/{family}/{verdict['status']}"
            accepted_statuses[status_key] = accepted_statuses.get(status_key, 0) + 1
        used = time.process_time_ns() - started
        for f in (family, "all"):
            k = f"{stage}/{f}/{row['arm']}"
            cpu[k] = cpu.get(k, 0) + used
    require(len(seen) == 64 * len(ARMS), "missing planned outputs")
    require(all(len(s) == 1 for s in statuses.values()), "UNKNOWN: conflicting accepted outcomes")
    costs = set()
    for line in (directory / "costs.jsonl").read_text().splitlines():
        row = json.loads(line, object_pairs_hook=verifier._pairs)
        key = row["stage"], row["task_hash"], row["arm"]
        require(
            key in seen and key not in costs and type(row["cpu_ns"]) is int and row["cpu_ns"] >= 0,
            "invalid or duplicate resource cost",
        )
        costs.add(key)
    require(costs == seen, "missing measured resource costs")
    return {
        "accepted": not rejected,
        "outputs": len(seen),
        "rejected": rejected,
        "check_cpu_ns": cpu,
        "history_check_cpu_ns": history_cpu,
        "memory_check_cpu_ns": memory_cpu,
        "accepted_statuses": accepted_statuses,
        "procedural_independence": True,
        "confirmation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--freeze-sha256", required=True)
    args = parser.parse_args()
    try:
        from contrib.invention_automation.readonly import enforce

        restriction = enforce()
        write_denied = socket_denied = False
        try:
            os.close(os.open(args.directory / "write-probe", os.O_WRONLY | os.O_CREAT, 0o600))
        except PermissionError:
            write_denied = True
        try:
            socket.socket().close()
        except PermissionError:
            socket_denied = True
        require(write_denied and socket_denied, "verifier OS restriction not demonstrated")
        result = verify(args.directory, args.freeze_sha256)
        require(
            "alpha_factory_v1.core.runtime.retained_experience.solver" not in sys.modules
            and "contrib.retained_experience.progressive" not in sys.modules,
            "verifier imported the candidate",
        )
        result.update(
            {
                "restriction": restriction,
                "write_denied": write_denied,
                "socket_denied": socket_denied,
                "candidate_imported": False,
            }
        )
        print(json.dumps(result, allow_nan=False))
        return 0 if result["accepted"] else 1
    except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, OSError, IndexError) as error:
        print(json.dumps({"accepted": False, "reason": str(error), "error": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

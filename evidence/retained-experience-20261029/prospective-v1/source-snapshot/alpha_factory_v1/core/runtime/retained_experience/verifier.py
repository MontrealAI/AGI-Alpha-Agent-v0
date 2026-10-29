# SPDX-License-Identifier: Apache-2.0
"""Read-only, independently reconstructed acceptance for retained-experience trials.

This verifier imports neither the producer nor the candidate. Its finite LP
checks share the historical Decimal checker and host, not external certification.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import socket
import sys
import time
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
GAP = Decimal("0.00001")
_checker_spec = importlib.util.spec_from_file_location(
    "_experience_decimal_checker", Path(__file__).parents[1] / "structural_transfer/eadarp_check.py"
)
if _checker_spec is None or _checker_spec.loader is None:
    raise RuntimeError("independent checker unavailable")
eadarp_check = importlib.util.module_from_spec(_checker_spec)
_checker_spec.loader.exec_module(eadarp_check)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=False).encode()


def hash_value(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def fingerprint(target: dict[str, Any]) -> str:
    """Exclude prose and identifiers so renaming old work cannot make it fresh."""
    body = {k: v for k, v in target.items() if k not in {"id", "need"}}
    body["updates"] = {k: str(Decimal(v).normalize()) for k, v in target["updates"].items()}
    body["assumptions"] = sorted(target["assumptions"])
    with localcontext() as context:
        context.prec = 250
        raw = "\n".join(
            " ".join(str(Decimal(token).normalize()) for token in line.split())
            for line in target["instance_text"].splitlines()
            if line.strip()
        )
    body["instance_text"], body["instance_sha256"] = raw, hashlib.sha256(raw.encode()).hexdigest()
    return hash_value(body)


def check_output(target: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    """Check feasibility AND an independently computed bounded dual optimality gap."""
    verdict = eadarp_check.check(target, output["artifact"], {})
    if verdict.get("accepted") is not True:
        return {"accepted": False, "reason": "independent certificate check", "detail": verdict}
    if output["artifact"]["status"] == "INFEASIBLE":
        return {"accepted": True, "status": "INFEASIBLE", "objective_gap": "0"}
    model = eadarp_check.independent_model(target)
    duals = output.get("duals")
    if not isinstance(duals, list) or len(duals) != len(model["vehicles"]):
        return {"accepted": False, "reason": "missing optimality evidence"}
    with localcontext() as context:
        context.prec = 250
        bound = Decimal(0)
        for item, dual in zip(model["vehicles"], duals):
            rows = {row["name"]: row for row in item["rows"]}
            if not isinstance(dual, dict) or not set(dual) <= set(rows):
                return {"accepted": False, "reason": "unknown dual rows"}
            residual = [Decimal(0)] * len(item["variables"])
            for index, value in item["objective"]["terms"]:
                residual[index] = Decimal(value)
            bound += Decimal(item["objective"]["constant"])
            for name, text in dual.items():
                weight = eadarp_check._dec(text)
                if weight > 0:
                    return {"accepted": False, "reason": "invalid dual sign"}
                row = rows[name]
                bound += weight * Decimal(row["rhs"])
                for index, value in row["terms"]:
                    residual[index] -= weight * Decimal(value)
            bound += sum(
                (min(r * Decimal(v["lower"]), r * Decimal(v["upper"])) for r, v in zip(residual, item["variables"])),
                Decimal(0),
            )
        gap = Decimal(output["artifact"]["objective"]) - bound
        accepted = -GAP <= gap <= GAP
        return {"accepted": accepted, "status": "FEASIBLE", "objective_gap": str(gap), "reason": "bounded dual gap"}


def check_memory(memory: dict[str, Any], history: list[dict[str, Any]]) -> None:
    """Bind reusable assets to checked historical outputs and actual constraints."""
    known = {hash_value(record["target"]): record for record in history}
    if not 1 <= len(history) <= 16 or len(memory["assets"]) > 64:
        raise ValueError("historical memory exceeds declared finite scope")
    for asset in memory["assets"]:
        if asset["source"] not in known:
            raise ValueError("retained asset has no verified historical origin")
        source = known[asset["source"]]
        artifact = source["output"]["artifact"]
        if asset["kind"] == "ray":
            if (
                artifact["status"] != "INFEASIBLE"
                or asset["weights"] != artifact["witness"]["rows"]
                or asset["vehicle"] != artifact["witness"]["vehicle"]
            ):
                raise ValueError("retained ray differs from its checked historical witness")
            continue
        if asset["kind"] != "basis" or artifact["status"] != "FEASIBLE":
            raise ValueError("unqualified retained method kind")
        vehicle = asset["vehicle"]
        model = eadarp_check.independent_model(source["target"])["vehicles"][vehicle]
        schedule = artifact["vehicles"][vehicle]
        expected_point = [Decimal(x) for key in ("start_min", "charge_min", "arrival_kwh") for x in schedule[key]]
        if [Decimal(x) for x in asset["point"]] != expected_point or asset["duals"] != source["output"]["duals"][
            vehicle
        ]:
            raise ValueError("retained point or dual differs from checked source")
        rows = {row["name"]: row for row in model["rows"]}
        size = len(expected_point)
        if (
            len(asset["row_names"]) != size
            or len(set(asset["row_names"])) != size
            or not set(asset["row_names"]) <= set(rows)
            or len(asset["inverse"]) != size
            or any(len(row) != size for row in asset["inverse"])
        ):
            raise ValueError("retained basis dimensions or row identities differ")
        for i, name in enumerate(asset["row_names"]):
            for j in range(size):
                product = sum(
                    (
                        Decimal(coefficient) * Decimal(asset["inverse"][index][j])
                        for index, coefficient in rows[name]["terms"]
                    ),
                    Decimal(0),
                )
                if not product.is_finite() or abs(product - int(i == j)) > Decimal("1e-7"):
                    raise ValueError("retained inverse does not invert the historical constraint set")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read(path: Path) -> Any:
    if path.is_symlink() or path.stat().st_size > 32_000_000:
        raise ValueError("unsupported evidence file")
    return json.loads(
        path.read_bytes(), object_pairs_hook=_pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x))
    )


def verify(directory: Path, expected_freeze: str) -> dict[str, Any]:
    """Reconcile the complete planned denominator and exact frozen code identities."""
    if hashlib.sha256((directory / "freeze.json").read_bytes()).hexdigest() != expected_freeze:
        raise ValueError("trusted freeze identity differs")
    freeze = read(directory / "freeze.json")
    for name, sha in freeze["sources"].items():
        if (
            Path(name).is_absolute()
            or ".." in Path(name).parts
            or hashlib.sha256((directory / "source-snapshot" / name).read_bytes()).hexdigest() != sha
        ):
            raise ValueError("frozen source snapshot missing or changed")
    if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha for name, sha in freeze["sources"].items()):
        raise ValueError("frozen implementation changed")
    protocol = read(directory / "protocol.json")
    if hash_value(protocol) != freeze["protocol_hash"]:
        raise ValueError("frozen acceptance or accounting protocol changed")
    if (
        hash_value(read(directory / "base.json")) != freeze["base_hash"]
        or hash_value(read(directory / "cost-policy.json")) != freeze["cost_policy_hash"]
    ):
        raise ValueError("base task or prospective cost policy changed")
    history = read(directory / "history.json")
    memory = read(directory / "memory.json")
    candidate_freeze = read(directory / "candidate-freeze.json")
    if memory["memory_hash"] != hash_value({k: v for k, v in memory.items() if k != "memory_hash"}):
        raise ValueError("frozen memory changed")
    if hash_value(memory) != candidate_freeze["memory_hash"]:
        raise ValueError("candidate changed after learning")
    if (
        hash_value(history) != candidate_freeze["history_hash"]
        or hash_value(read(directory / "ordinary-cache.json")) != candidate_freeze["ordinary_cache_hash"]
        or hash_value(read(directory / "lifecycle.json")) != candidate_freeze["lifecycle_hash"]
    ):
        raise ValueError("historical inputs, conventional cache or lifecycle costs changed")
    if memory["training"] != [hash_value(r["target"]) for r in history]:
        raise ValueError("memory lineage differs from training")
    known = {fingerprint(r["target"]) for r in history}
    for record in history:
        if check_output(record["target"], record["output"])["accepted"] is not True:
            raise ValueError("unverified training output")
    check_memory(memory, history)
    training_tasks = read(directory / "training-tasks.json")
    training_by_hash = {hash_value(task): task for task in training_tasks}
    if len(training_by_hash) != 1 + len(protocol["regimes"]) * protocol["development_per_regime"]:
        raise ValueError("development task denominator differs")
    development = read(directory / "development.json")
    fixed_methods = {arm for arm in protocol["arms"] if arm.startswith("highs")}
    development_keys: set[tuple[str, str]] = set()
    for trial in development:
        development_key = (trial["target_hash"], trial["arm"])
        if (
            development_key in development_keys
            or development_key[0] not in training_by_hash
            or development_key[1] not in fixed_methods
        ):
            raise ValueError("development comparison omitted or duplicated an alternative")
        if check_output(training_by_hash[development_key[0]], trial["output"])["accepted"] is not True:
            raise ValueError("unverified development comparator")
        development_keys.add(development_key)
    if len(development_keys) != len(training_tasks) * len(fixed_methods):
        raise ValueError("development comparator denominator differs")
    tasks = read(directory / "tasks.json")
    if len(tasks) != protocol["cases_per_regime"] * len(protocol["regimes"]):
        raise ValueError("planned task denominator changed")
    seen: set[str] = set()
    for task in tasks:
        identity = fingerprint(task)
        if identity in known or identity in seen:
            raise ValueError("task content reused across training or evaluation")
        seen.add(identity)
    cases = {hash_value(task): task for task in tasks}
    identities: set[tuple[str, str, int]] = set()
    rejected, accepted, feasible = [], 0, 0
    arm_cpu = {arm: 0 for arm in protocol["arms"]}
    statuses: dict[str, set[str]] = {}
    ledger = {}
    for line in (directory / "costs.jsonl").read_text().splitlines():
        event = json.loads(line, object_pairs_hook=_pairs)
        key = (event["task_hash"], event["arm"], event["repeat"])
        if key in ledger or type(event["cpu_ns"]) is not int or event["cpu_ns"] < 0:
            raise ValueError("duplicate cost identity or invalid measured cost")
        ledger[key] = event
    for line in (directory / "observations.jsonl").read_text().splitlines():
        check_started = time.process_time_ns()
        record = json.loads(line, object_pairs_hook=_pairs)
        key = (record["task_hash"], record["arm"], record["repeat"])
        if (
            key in identities
            or key[0] not in cases
            or key[1] not in protocol["arms"]
            or type(key[2]) is not int
            or not 0 <= key[2] < protocol["repeats"]
        ):
            raise ValueError("duplicated or unplanned observation")
        identities.add(key)
        if type(record["cpu_ns"]) is not int or record["cpu_ns"] < 0 or record["wall_ns"] < 0:
            raise ValueError("invalid measured costs")
        if key not in ledger or ledger[key]["cpu_ns"] < record["cpu_ns"]:
            raise ValueError("missing or understated delivered-work cost")
        if "output" not in record:
            rejected.append({"key": key, "reason": record.get("failure", "missing output")})
            arm_cpu[key[1]] += time.process_time_ns() - check_started
            continue
        verdict = check_output(cases[key[0]], record["output"])
        if verdict["accepted"] is not True:
            rejected.append({"key": key, "reason": verdict})
        else:
            accepted += 1
            feasible += int(verdict["status"] == "FEASIBLE")
            statuses.setdefault(key[0], set()).add(verdict["status"])
        arm_cpu[key[1]] += time.process_time_ns() - check_started
    expected = len(tasks) * len(protocol["arms"]) * protocol["repeats"]
    if len(identities) != expected or set(ledger) != identities:
        raise ValueError("planned observations missing")
    for task_hash, alternatives in statuses.items():
        if len(alternatives) != 1:
            rejected.append({"task_hash": task_hash, "reason": "UNKNOWN: conflicting accepted outcomes"})
    return {
        "schema": "agialpha/experience-verification/v1",
        "freeze_verified": True,
        "planned": expected,
        "observed": len(identities),
        "accepted": accepted,
        "feasible_schedules": feasible,
        "rejected": rejected,
        "memory_hash": hash_value(memory),
        "tasks_hash": hash_value(tasks),
        "observations_sha256": hashlib.sha256((directory / "observations.jsonl").read_bytes()).hexdigest(),
        "costs_sha256": hashlib.sha256((directory / "costs.jsonl").read_bytes()).hexdigest(),
        "arm_check_cpu_ns": arm_cpu,
        "confirmation": False,
        "independence": "procedural separation; shared author, host, checker and libraries",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--freeze-sha256", required=True)
    args = parser.parse_args()
    started = time.process_time_ns()
    try:
        from contrib.invention_automation.readonly import enforce

        restriction = enforce()
        denied = False
        try:
            fd = os.open(args.directory / "verifier-write-probe", os.O_WRONLY | os.O_CREAT, 0o600)
            os.close(fd)
        except PermissionError:
            denied = True
        sockets_denied = False
        try:
            probe = socket.socket()
            probe.close()
        except PermissionError:
            sockets_denied = True
        if not denied or not sockets_denied:
            raise ValueError("verifier OS restrictions not demonstrated")
        result = verify(args.directory, args.freeze_sha256)
        candidate_imported = "alpha_factory_v1.core.runtime.retained_experience.solver" in sys.modules
        if candidate_imported:
            raise ValueError("separate verifier imported the candidate")
        result.update(
            {
                "restrictions": restriction,
                "candidate_write_denied_by_os": denied,
                "new_socket_denied_by_os": sockets_denied,
                "candidate_imported": candidate_imported,
                "cpu_ns": time.process_time_ns() - started,
            }
        )
        print(json.dumps(result, allow_nan=False))
        return 0 if not result["rejected"] else 1
    except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, OSError, IndexError) as error:
        print(json.dumps({"accepted": False, "error": type(error).__name__, "reason": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

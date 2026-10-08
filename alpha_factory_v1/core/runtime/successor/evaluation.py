# SPDX-License-Identifier: Apache-2.0
"""Independently operable fresh examination of a frozen bounded artifact.

The default custodian is a separate local process, not an independent organization.
Only a corpus commitment leaves this interface; each new invocation is a new measurement.
"""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import platform
import random
import re
import secrets
import statistics
import sys
import threading
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..store import private_write
from .aggregation import BETA, CURRENT, MAX_DURATION_US, contract, execute, validate_program
from .protocol import canonical, digest, safe_json_loads

MANIFEST_KEYS = {
    "schema_version",
    "mission",
    "request_hash",
    "mission_contract",
    "program",
    "implementation",
    "supplier",
    "world",
    "policy",
    "tools",
    "memory",
    "environment",
    "comparators",
    "proof_protocol",
    "economics",
    "formation",
    "parent_release",
    "frozen_at_ms",
}
_MEMORY_MEASUREMENT_LOCK = threading.Lock()


def implementation_manifest() -> dict[str, str]:
    """Bind trusted interpreter and evaluator bytes rather than a mutable module label."""
    root = Path(__file__).parent
    return {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in ("aggregation.py", "evaluation.py")
    }


def host_environment() -> dict[str, Any]:
    """Describe the actual local environment without paths, secrets or machine identity."""
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "timer": "perf_counter_ns",
        "timer_resolution_ns": max(1, int(time.get_clock_info("perf_counter").resolution * 1_000_000_000)),
        "load_isolation": "uncontrolled local host; paired randomized order mitigates but does not remove noise",
    }


def proof_protocol(max_events: int) -> dict[str, Any]:
    """Preregister all examination rules before protected observations exist."""
    return {
        "version": 1,
        "interface": "successor.evaluation.evaluate_frozen/v1",
        "valid_workloads": 12,
        "max_events": max_events,
        "warmups": 1,
        "repetitions": 3,
        "order": "random permutation of fixed complete systems within each workload and repetition",
        "timing": "validation plus aggregation plus deterministic projection; corpus construction excluded",
        "memory": "tracemalloc peak in separate untimed call; input allocated before start",
        "correctness": "all valid cases equal independent sorted reducer; all malformed cases reject",
        "max_case_time_ns": 2_000_000_000,
        "max_case_peak_bytes": 64_000_000,
        "max_verifier_seconds": 90,
        "minimum_advantage_bps": 500,
        "tie_margin_bps": 200,
        "bootstrap_samples": 399,
        "interval": "paired percentile bootstrap; Bonferroni 97.5% per two fixed comparisons; descriptive only",
        "unit": "independently generated workload, not timing repetition or event",
        "freshness": "fresh custodian entropy after freeze, never returned to formation",
        "hard_gates": ["correctness", "malformed_rejection", "time", "peak_memory", "closed_grammar"],
        "required_qualification": ["external-verifier", "competent-frontier-coding-agent", "accountable-admission"],
        "validity_seconds": 86400,
    }


def economics() -> dict[str, Any]:
    """One explicit cost convention, without converting modeled savings into money."""
    return {
        "version": 1,
        "utility_unit": "negative-nanoseconds-per-workload",
        "amortization_workloads": 10_000,
        "rule": (
            "mean of per-workload median runtime + (formation + proof + switching) / amortization; "
            "comparators use mean of workload medians"
        ),
        "switching_ns": 0,
        "switching_assumption": "pure local callable replacement only; operational migration/recovery costs unmeasured",
        "measured_money": None,
        "human_review_ns": None,
        "external_provider_money": None,
        "accepted_realized_value": None,
        "unknown_cost_effect": "blocks economic Alpha and production resource allocation",
        "frontier_status": "unavailable, not a zero-cost comparator",
    }


def validate_frozen(frozen: dict[str, Any]) -> dict[str, Any]:
    """Reject stale behavior, changed comparators or examination terms before execution."""
    # Exact builtin types reject bool/int substitution and arbitrary subclasses.
    if type(frozen) is not dict or set(frozen) != {"schema_version", "manifest", "release_digest"}:  # noqa: E721
        raise ValueError("invalid freeze envelope")
    if type(frozen["schema_version"]) is not int or frozen["schema_version"] != 1:  # noqa: E721
        raise ValueError("unsupported freeze version")
    manifest = frozen["manifest"]
    if type(manifest) is not dict or set(manifest) != MANIFEST_KEYS:  # noqa: E721
        raise ValueError("incomplete or unsupported release manifest")
    if digest("release", manifest) != frozen["release_digest"]:
        raise ValueError("freeze commitment mismatch; new release and examination required")
    if manifest["mission"] != "streaming-metrics-v1" or manifest["schema_version"] != 1:
        raise ValueError("unsupported mission manifest")
    frozen_at_ms = manifest["frozen_at_ms"]
    if type(frozen_at_ms) is not int or not 0 <= frozen_at_ms <= time.time_ns() // 1_000_000:  # noqa: E721
        raise ValueError("invalid or future freeze timestamp")
    validate_program(manifest["program"])
    if manifest["implementation"] != implementation_manifest() or manifest["mission_contract"] != contract():
        raise ValueError("implementation or mission semantics changed after freeze")
    environment = manifest["environment"]
    if environment.get("host") != host_environment():
        raise ValueError("operating environment changed; create a new release for requalification")
    maximum = environment.get("max_events")
    if type(maximum) is not int or not 64 <= maximum <= 20_000:  # noqa: E721
        raise ValueError("invalid environment bound")
    if manifest["proof_protocol"] != proof_protocol(maximum) or manifest["economics"] != economics():
        raise ValueError("unsupported or mutated examination/cost rules")
    if manifest["comparators"] != comparator_manifest():
        raise ValueError("comparator set changed")
    if manifest["tools"] != [] or manifest["policy"] != selection_policy():
        raise ValueError("unsupported tool or policy capability")
    formation = manifest["formation"]
    if type(formation) is not dict or set(formation) != {  # noqa: E721
        "total_runtime_ns",
        "source_sha256",
        "attempts_digest",
        "configuration",
        "prompts",
        "routing",
    }:
        raise ValueError("unsupported formation manifest")
    total_runtime_ns = formation["total_runtime_ns"]
    if type(total_runtime_ns) is not int or not 0 <= total_runtime_ns <= 600_000_000_000:  # noqa: E721
        raise ValueError("formation cost must be a nonnegative bounded integer measurement")
    if formation["source_sha256"] != hashlib.sha256((Path(__file__).parent / "mission.py").read_bytes()).hexdigest():
        raise ValueError("formation implementation changed after freeze")
    if not isinstance(formation["attempts_digest"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", formation["attempts_digest"]
    ):
        raise ValueError("invalid formation attempts commitment")
    if type(manifest["memory"]) is not dict or set(manifest["memory"]) != {"admitted", "digest"}:  # noqa: E721
        raise ValueError("invalid memory binding")
    if manifest["memory"]["digest"] != digest("memory", manifest["memory"]["admitted"]):
        raise ValueError("memory commitment mismatch")
    return manifest


def current_comparator_manifest(frozen: dict[str, Any]) -> dict[str, Any]:
    """Bind Current's exact membership in the frozen trial before its outcomes exist."""
    frozen = copy.deepcopy(frozen)
    manifest = validate_frozen(frozen)
    subject = {
        "schema_version": 1,
        "role": "current-comparator",
        "artifact": manifest["comparators"]["current"]["artifact"],
        "implementation": manifest["implementation"],
        "mission_contract": manifest["mission_contract"],
        "environment": manifest["environment"],
        "proof_protocol": manifest["proof_protocol"],
        "trial_release_digest": frozen["release_digest"],
        "comparator_hash": digest("comparators", manifest["comparators"]),
        "frozen_at_ms": manifest["frozen_at_ms"],
    }
    return {"manifest": subject, "subject_digest": digest("current-comparator", subject)}


def comparator_manifest() -> dict[str, Any]:
    """Bind feasible local software and disclose the unexecuted frontier alternative."""
    return {
        "current": {"artifact": CURRENT, "rationale": "competent one-pass dictionary incumbent", "status": "measured"},
        "beta": {"artifact": BETA, "rationale": "independent sorted groupby reducer", "status": "measured"},
        "frontier": {"status": "unavailable", "configuration": None, "reason": "no authorized frontier trial"},
        "allowances": "same workload, output contract, timeout and peak allocation limits for each fixed system",
        "selection": "best fixed feasible comparator by preregistered paired aggregate cost, never a per-case oracle",
    }


def selection_policy() -> dict[str, Any]:
    """Development policy; WORLD determines order and penalizes falsified resource assumptions."""
    return {
        "version": 1,
        "hard_gate": "all development correctness cases and malformed rejections pass",
        "priority": "ascending WORLD predicted work units; tie resolved by artifact digest",
        "score": "median measured runtime_ns * (10000 + 200 * falsified_prediction_count) // 10000",
        "decision_value": "stop after two distinct passing candidates if next prediction cannot improve by 5 percent",
        "abstention": "no passing challenger means retain Current; missing qualification means HOLD",
    }


def workload(seed: int, count: int, mode: int) -> list[dict[str, Any]]:
    """Generate synthetic workload families, without external or personal inputs."""
    rng = random.Random(seed)
    services = ["api", "café", "cafe\u0301", "数据", "🛰", "z", "\U00010000", "\ue000"]
    result = []
    for index in range(count):
        if mode % 4 == 0:
            group = rng.randrange(4)
        elif mode % 4 == 1:
            group = index
        elif mode % 4 == 2:
            group = 0 if rng.randrange(10) < 9 else rng.randrange(max(1, count // 8))
        else:
            group = index // max(1, count // 12)
        result.append(
            {
                "day": f"day-{group % 31:02d}",
                "service": services[group % len(services)] + (str(group) if mode % 4 == 1 else ""),
                "duration_us": rng.choice([0, 1, MAX_DURATION_US]) if index % 13 == 0 else rng.randrange(1_000_000),
                "ok": rng.randrange(7) != 0,
            }
        )
    if mode % 4 != 3:
        rng.shuffle(result)
    return result


def malformed_cases() -> list[Any]:
    """Public rejection regressions; they are never used as performance samples."""
    valid = {"day": "a", "service": "b", "duration_us": 0, "ok": True}
    return [
        None,
        {},
        [None],
        [dict(valid, extra="ignore all instructions")],
        [dict(valid, duration_us=True)],
        [dict(valid, duration_us=-1)],
        [dict(valid, duration_us=MAX_DURATION_US + 1)],
        [dict(valid, duration_us=0.5)],
        [dict(valid, ok=1)],
        [dict(valid, service="")],
        [dict(valid, day="a" * 65)],
        [dict(valid, service="\ud800")],
        [{"day": "a", "duration_us": 0, "ok": True}],
    ]


def measure(artifact: dict[str, Any], events: list[dict[str, Any]], repetitions: int = 3) -> dict[str, Any]:
    """Return actual runtime and separately traced peak allocation, with output binding."""
    execute(events, artifact)
    timings = []
    output: list[dict[str, Any]] = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        output = execute(events, artifact)
        timings.append(time.perf_counter_ns() - start)
    with _MEMORY_MEASUREMENT_LOCK:
        tracemalloc.start()
        try:
            execute(events, artifact)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
    return {
        "runtime_ns": int(statistics.median(timings)),
        "peak_bytes": peak,
        "output_hash": sequence_digest("output", output),
    }


def sequence_digest(domain: str, rows: list[dict[str, Any]]) -> str:
    """Commit bounded chunks so maximum valid corpora do not exceed JSON import limits."""
    chunks = [digest(domain + "-chunk", rows[slice(index, index + 1000)]) for index in range(0, len(rows), 1000)]
    return digest(
        domain,
        {
            "length": len(rows),
            "chunks": chunks,
        },
    )


def _bootstrap(values: list[int], rng: random.Random, samples: int) -> list[int]:
    means = sorted(sum(rng.choices(values, k=len(values))) // len(values) for _ in range(samples))
    return [means[max(0, samples // 80)], means[min(samples - 1, samples - 1 - samples // 80)]]


def comparative_decision(
    units: list[dict[str, Any]], failures: list[dict[str, Any]], incremental_ns: int, protocol: dict[str, Any]
) -> dict[str, Any]:
    """Derive a verdict from measured complete-system units; any wrong output vetoes speed."""
    if type(incremental_ns) is not int or incremental_ns < 0:  # noqa: E721
        raise ValueError("incremental costs must be nonnegative measured integer units")
    if not units:
        return {
            "local_verdict": "INSUFFICIENT_EVIDENCE",
            "qualification_verdict": "HOLD",
            "best_fixed_comparator": None,
            "comparisons": {},
            "incremental_cost_ns_per_workload": incremental_ns,
            "independent_units": 0,
            "alpha_established": False,
            "specialist_asi_designation": False,
            "reason": "no independent evaluation units",
        }
    for unit in units:
        for name in ("current", "beta", "candidate"):
            timing = unit["systems"][name]["runtime_ns"]
            if type(timing) is not int or timing < 0:  # noqa: E721
                raise ValueError("runtime measurements must be nonnegative integer nanoseconds")
    totals = {
        name: sum(unit["systems"][name]["runtime_ns"] for unit in units) for name in ("current", "beta", "candidate")
    }
    count = len(units)
    best = min(("current", "beta"), key=lambda name: totals[name])
    comparisons = {}
    for name in ("current", "beta"):
        values = [
            unit["systems"][name]["runtime_ns"] - unit["systems"]["candidate"]["runtime_ns"] - incremental_ns
            for unit in units
        ]
        interval = _bootstrap(values, random.Random(7231), protocol["bootstrap_samples"])
        mean = sum(values) // max(1, count)
        baseline = totals[name] // max(1, count)
        comparisons[name] = {
            "advantage_ns": mean,
            "advantage_bps": mean * 10_000 // max(1, baseline),
            "interval_ns": interval,
        }
    failed = any(item["system"] == "candidate" for item in failures)
    comparator_failed = any(item["system"] != "candidate" for item in failures)
    advantage = comparisons[best]["advantage_bps"]
    if failed:
        verdict = "FAIL"
    elif comparator_failed or count != protocol["valid_workloads"]:
        verdict = "INSUFFICIENT_EVIDENCE"
    elif advantage < -protocol["tie_margin_bps"]:
        verdict = "RETAIN_INCUMBENT" if best == "current" else "RETAIN_ALTERNATIVE"
    elif abs(advantage) <= protocol["tie_margin_bps"]:
        verdict = "TIE"
    elif all(
        item["interval_ns"][0] > 0 and item["advantage_bps"] >= protocol["minimum_advantage_bps"]
        for item in comparisons.values()
    ):
        verdict = "LOCAL_ADVANTAGE"
    else:
        verdict = "INSUFFICIENT_EVIDENCE"
    return {
        "local_verdict": verdict,
        "qualification_verdict": "HOLD",
        "best_fixed_comparator": best,
        "comparisons": comparisons,
        "incremental_cost_ns_per_workload": incremental_ns,
        "independent_units": count,
        "alpha_established": False,
        "specialist_asi_designation": False,
        "reason": (
            "local descriptive comparison; missing external verifier, frontier alternative, "
            "money/review costs and admission"
        ),
    }


def evaluate_frozen(frozen: dict[str, Any], checkpoint: Callable[[], None] | None = None) -> dict[str, Any]:
    """Execute a new protected examination; never reuse development labels or timings."""
    frozen = copy.deepcopy(frozen)
    manifest = validate_frozen(frozen)
    examined_at_ms = time.time_ns() // 1_000_000
    check = checkpoint or (lambda: None)
    protocol = manifest["proof_protocol"]
    started = time.perf_counter_ns()
    seed = secrets.randbits(128)
    rng = random.Random(seed)
    artifacts = {"current": CURRENT, "beta": BETA, "candidate": manifest["program"]}
    counts = [0, 1, 8, 31, protocol["max_events"] // 2, protocol["max_events"]] * 2
    private_corpus = [workload(rng.getrandbits(128), count, i) for i, count in enumerate(counts)]
    corpus_commitment = digest(
        "protected-corpus",
        {
            "nonce": secrets.token_hex(32),
            "workloads": [sequence_digest("private-workload", rows) for rows in private_corpus],
        },
    )
    failures: list[dict[str, Any]] = []
    units = []
    for index, events in enumerate(private_corpus):
        check()
        expected = execute(events, BETA)
        expected_hash = sequence_digest("output", expected)
        order = list(artifacts)
        rng.shuffle(order)
        systems: dict[str, Any] = {}
        raw_timings: dict[str, list[int]] = {name: [] for name in artifacts}
        for name in order:
            execute(events, artifacts[name])
        orders = []
        for _ in range(protocol["repetitions"]):
            rng.shuffle(order)
            orders.append(list(order))
            for name in order:
                begin = time.perf_counter_ns()
                output = execute(events, artifacts[name])
                elapsed = time.perf_counter_ns() - begin
                raw_timings[name].append(elapsed)
                if output != expected:
                    failures.append({"system": name, "case": index, "gate": "correctness"})
        for name in order:
            gc.collect()
            measurement = measure(artifacts[name], events, repetitions=1)
            measurement["runtime_ns"] = int(statistics.median(raw_timings[name]))
            measurement["timings_ns"] = raw_timings[name]
            systems[name] = measurement
            if measurement["output_hash"] != expected_hash:
                failures.append({"system": name, "case": index, "gate": "correctness"})
            if max(raw_timings[name]) > protocol["max_case_time_ns"]:
                failures.append({"system": name, "case": index, "gate": "time"})
            if measurement["peak_bytes"] > protocol["max_case_peak_bytes"]:
                failures.append({"system": name, "case": index, "gate": "peak_memory"})
        units.append(
            {"unit": index, "family": index % 4, "event_count": len(events), "orders": orders, "systems": systems}
        )
        if time.perf_counter_ns() - started > protocol["max_verifier_seconds"] * 1_000_000_000:
            raise TimeoutError("verifier exceeded its fixed total budget")
    malformed = malformed_cases()
    for name, artifact in artifacts.items():
        for index, bad in enumerate(malformed):
            check()
            try:
                execute(bad, artifact)
            except ValueError:
                continue
            failures.append({"system": name, "case": index, "gate": "malformed_rejection"})
    elapsed = time.perf_counter_ns() - started
    formation_ns = manifest["formation"]["total_runtime_ns"]
    incremental = (formation_ns + elapsed + manifest["economics"]["switching_ns"]) // manifest["economics"][
        "amortization_workloads"
    ]
    decision = comparative_decision(units, failures, incremental, protocol)
    return {
        "schema_version": 1,
        "release_digest": frozen["release_digest"],
        "request_hash": manifest["request_hash"],
        "protocol_hash": digest("proof-protocol", protocol),
        "environment_hash": digest("environment", manifest["environment"]),
        "comparator_hash": digest("comparators", manifest["comparators"]),
        "protected_evidence_commitment": corpus_commitment,
        "measurement_id": secrets.token_hex(16),
        "observed_at_ms": time.time_ns() // 1_000_000,
        "examined_at_ms": examined_at_ms,
        "issued_at_ms": time.time_ns() // 1_000_000,
        "valid_until_ms": time.time_ns() // 1_000_000 + protocol["validity_seconds"] * 1000,
        "custody": {
            "identity": "local-process-custodian",
            "organization_independent": False,
            "control_independent": False,
            "funding": "same local operator",
            "protocol_control": "repository release; protocol frozen before corpus acquisition",
            "protected_data_exported": False,
            "replication": (
                "new invocation creates fresh workloads and a new receipt; timings are not deterministic replay"
            ),
        },
        "scope": "local-native-rehearsal",
        "units": units,
        "malformed_cases": len(malformed),
        "failures": failures,
        "exclusions": [],
        "interventions": [],
        "costs": {
            "verifier_runtime_ns": elapsed,
            "human_review_ns": None,
            "money": None,
            "formation_cost_provenance": "supplied-frozen-record; not independently authenticated by custodian",
        },
        "decision": decision,
    }


def main() -> None:
    """Run the packaged verifier in a distinct custodian-controlled process."""
    parser = argparse.ArgumentParser(description="Fresh local examination; not an externally independent certification")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--stdio", action="store_true")
    args = parser.parse_args()
    if not args.stdio and (not args.input or not args.output):
        parser.error("provide --input and --output, or --stdio")
    if not args.stdio and (args.output.exists() or args.output.is_symlink()):
        raise FileExistsError("output already exists; choose a new report path")
    if args.stdio:
        raw = sys.stdin.buffer.read(1_048_577)
        frozen = safe_json_loads(raw, max_bytes=1_048_576)
    else:
        from .transport import read_document

        frozen = read_document(args.input, max_bytes=1_048_576)
    result = evaluate_frozen(frozen)
    data = canonical(result)
    if args.stdio:
        sys.stdout.buffer.write(data)
    else:
        private_write(args.output, data + b"\n")


if __name__ == "__main__":
    main()

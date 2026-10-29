# SPDX-License-Identifier: Apache-2.0
"""Replay saved unresolved observations with a read-only trace of rejected candidates.

This does not recover original inner artifact bytes. It produces separately
costed diagnostic evidence from the exact saved request and chronological memory,
without changing the frozen engine, strategies, acceptance, seeds, or budget.
"""

from __future__ import annotations

import argparse
import copy
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
from types import FrameType
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from alpha_factory_v1.core.runtime.compounding_discovery import engine
from alpha_factory_v1.core.runtime.structural_transfer import eadarp_check
from contrib.compounding_discovery.audit import audit_frozen_files, digest
from contrib.compounding_discovery.experiment import storage_guard


def read(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def write(path: Path, document: Any) -> None:
    raw = json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    if path.suffix == ".gz":
        raw = gzip.compress(raw, mtime=0)
    with path.open("xb") as stream:
        stream.write(raw)


def replay(record: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
    """Observe execute-frame locals on exceptions; never assign to candidate state."""
    request = record["request"]
    if record["memory_version"] != digest(memory) or record["result"]["memory_before_hash"] != memory["memory_hash"]:
        raise ValueError("saved chronological memory does not match the original observation")
    traces: list[dict[str, Any]] = []

    def trace(frame: FrameType, event: str, arg: Any) -> Any:
        if frame.f_code is not engine.execute.__code__:
            return None
        if event == "exception" and issubclass(arg[0], ValueError):
            local = frame.f_locals
            captured = {
                key: copy.deepcopy(local[key])
                for key in ("candidates", "artifact", "verdict", "critiques")
                if key in local
            }
            if "meter" in local:
                captured["resource_snapshot"] = copy.deepcopy(local["meter"].snapshot())
            traces.append(
                {
                    "error_type": arg[0].__name__,
                    "error_text": str(arg[1]),
                    "engine_line": frame.f_lineno,
                    "locals": captured,
                }
            )
        return trace

    started_cpu, started_wall = time.process_time_ns(), time.perf_counter()
    previous = sys.gettrace()
    outcome: dict[str, Any]
    try:
        sys.settrace(trace)
        result = engine.execute(copy.deepcopy(request), copy.deepcopy(memory))
        outcome = {"accepted": result["acceptance"]["accepted"], "result": result}
    except Exception as error:
        outcome = {"accepted": False, "error_type": type(error).__name__, "error_text": str(error)}
    finally:
        sys.settrace(previous)
    candidates = traces[-1]["locals"].get("candidates", []) if traces else []
    checked = [
        {
            "candidate_index": index,
            "program": candidate.get("program"),
            "artifact_hash": digest(candidate["artifact"]),
            "independent_acceptance": eadarp_check.check(request["target"], candidate["artifact"]),
        }
        for index, candidate in enumerate(candidates)
        if "artifact" in candidate
    ]
    return {
        "schema": "agialpha/rejection-diagnostic/v1",
        "original_request_hash": digest(request),
        "original_result_hash": record["result"]["result_hash"],
        "original_accepted": record["accepted"],
        "request": request,
        "memory_hash": memory["memory_hash"],
        "source_hashes": engine.source_hashes(),
        "new_replay_outcome": outcome,
        "new_exception_traces": traces,
        "new_independent_candidate_checks": checked,
        "measurement": {
            "cpu_seconds": str(Fraction(time.process_time_ns() - started_cpu, 10**9)),
            "wall_seconds": str(time.perf_counter() - started_wall),
        },
        "scope": "New diagnostic replay; original missing inner bytes are not recovered; no training, promotion or confirmation",
    }


def run(campaign: Path, output: Path, maximum: int) -> dict[str, Any]:
    """Replay at most eight saved failures after externally checking frozen sources."""
    freeze = read(campaign / "freeze.json")
    audit_frozen_files(freeze["sources"])
    if engine.source_hashes() != freeze["engine_source_hashes"]:
        raise ValueError("frozen candidate source mismatch")
    if not 1 <= maximum <= 8 or any(parent.is_symlink() for parent in (output, *output.parents)):
        raise ValueError("bounded count and regular exclusive output required")
    output.mkdir(parents=True, exist_ok=False)
    write(
        output / "freeze.json",
        {
            "campaign": str(campaign),
            "campaign_freeze_hash": digest(freeze),
            "candidate_hashes": freeze["engine_source_hashes"],
            "diagnostic_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "policy": "read-only trace, exact original requests/budgets/seeds/memory, no tuning",
        },
    )
    start = time.process_time_ns()
    outcomes, reasons = [], {}
    for path in sorted((campaign / "learning").rglob("*.json.gz")):
        record = read(path)
        if record["accepted"] or len(outcomes) >= maximum:
            continue
        checkpoint = record["checkpoint"]
        if record["arm"] in {"cumulative", "retrieval"} and checkpoint:
            memory = read(campaign / f"memory-{checkpoint}.json")
        elif record["arm"] in {"cumulative", "retrieval", "frozen", "reset"}:
            memory = engine.empty_memory()
        else:
            raise ValueError("unsupported chronological diagnostic arm")
        guard = storage_guard(output, "observation", record["request"]["id"])
        report = replay(record, memory)
        report["original_record"] = str(path.relative_to(campaign))
        report["storage_guard_id"] = guard["id"]
        name = f"diagnostic-{len(outcomes):02d}.json.gz"
        write(output / name, report)
        for checked in report["new_independent_candidate_checks"]:
            for reason in checked["independent_acceptance"]["reasons"]:
                reasons[reason] = reasons.get(reason, 0) + 1
        outcomes.append(
            {
                "file": name,
                "original_record": report["original_record"],
                "replay_accepted": report["new_replay_outcome"]["accepted"],
                "captured_candidate_artifacts": len(report["new_independent_candidate_checks"]),
            }
        )
    audit_frozen_files(freeze["sources"])
    elapsed = Fraction(time.process_time_ns() - start, 10**9)
    summary = {
        "schema": "agialpha/rejection-diagnostic-summary/v1",
        "replays": outcomes,
        "recomputed_checker_reasons": reasons,
        "resource_event": {
            "id": "diagnostic-enclosing-cpu",
            "quantity_seconds": str(elapsed),
            "rate_usd_per_second": "1/36000",
            "amount_usd": str(elapsed / 36000),
        },
        "cost_scope": "Enclosing CPU includes traced engine and checker work; nested runtime events are included, not additive; startup and final summary serialization excluded",
        "all_frozen_sources_unchanged": True,
        "scope": "Diagnostic replay only; no original missing bytes recovered and no new fresh evaluation claim",
    }
    write(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(run(args.campaign, args.output, args.maximum), indent=2))


if __name__ == "__main__":
    main()

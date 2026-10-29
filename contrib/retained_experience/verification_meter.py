# SPDX-License-Identifier: Apache-2.0
"""Time unchanged archived verifier calls inside its existing read-only process."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

VERIFIER = "alpha_factory_v1/core/runtime/retained_experience/verifier.py"
READONLY = "contrib/invention_automation/readonly.py"


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("archived verifier unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def measure(directory: Path, expected_freeze: str) -> dict[str, Any]:
    started = time.process_time_ns()
    snapshot = directory / "source-snapshot"
    verifier: Any = load_module(snapshot / VERIFIER, "_scaling_archived_verifier")
    readonly = load_module(snapshot / READONLY, "_scaling_archived_readonly")
    history_count = len(verifier.read(directory / "history.json"))
    development_count = len(verifier.read(directory / "development.json"))
    protocol = verifier.read(directory / "protocol.json")
    output_count = protocol["cases_per_regime"] * len(protocol["regimes"]) * len(protocol["arms"]) * protocol["repeats"]
    timings = {name: 0 for name in ("history_outputs", "development_outputs", "memory", "evaluation_outputs")}
    calls = dict.fromkeys(timings, 0)
    output_check, memory_check = verifier.check_output, verifier.check_memory
    output_index = 0

    def timed_output(target: Any, output: Any) -> Any:
        nonlocal output_index
        name = (
            "history_outputs"
            if output_index < history_count
            else "development_outputs" if output_index < history_count + development_count else "evaluation_outputs"
        )
        output_index += 1
        before = time.process_time_ns()
        try:
            return output_check(target, output)
        finally:
            timings[name] += time.process_time_ns() - before
            calls[name] += 1

    def timed_memory(memory: Any, history: Any) -> None:
        before = time.process_time_ns()
        try:
            memory_check(memory, history)
        finally:
            timings["memory"] += time.process_time_ns() - before
            calls["memory"] += 1

    verifier.check_output, verifier.check_memory = timed_output, timed_memory
    restrictions = readonly.enforce()
    write_denied = sockets_denied = False
    try:
        fd = os.open(directory / "verifier-write-probe", os.O_WRONLY | os.O_CREAT, 0o600)
        os.close(fd)
    except PermissionError:
        write_denied = True
    try:
        probe = socket.socket()
        probe.close()
    except PermissionError:
        sockets_denied = True
    if not write_denied or not sockets_denied:
        raise ValueError("actual read-only verifier probes must refuse")
    verify_started = time.process_time_ns()
    result: dict[str, Any] = verifier.verify(directory, expected_freeze)
    verify_cpu = time.process_time_ns() - verify_started
    if calls != {
        "history_outputs": history_count,
        "development_outputs": development_count,
        "memory": 1,
        "evaluation_outputs": output_count,
    }:
        raise ValueError("metered native call denominator differs")
    if any(name.endswith(".solver") for name in sys.modules):
        raise ValueError("verifier imported a candidate solver")
    result.update(
        {
            "restrictions": restrictions,
            "candidate_write_denied_by_os": write_denied,
            "new_socket_denied_by_os": sockets_denied,
            "candidate_imported": False,
            "cpu_ns": time.process_time_ns() - started,
            "meter": {
                "call_cpu_ns": timings,
                "calls": calls,
                "verify_cpu_ns": verify_cpu,
                "unclassified_verify_cpu_ns": verify_cpu - sum(timings.values()),
                "classification": "history/development/memory calls are fixed only for this exact frozen history",
                "remainder": "unclassified; never assumed fixed or removed from lifecycle cost",
            },
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--freeze-sha256", required=True)
    args = parser.parse_args()
    try:
        result = measure(args.directory, args.freeze_sha256)
        print(json.dumps(result, allow_nan=False))
        return int(bool(result["rejected"]))
    except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError, OSError, IndexError) as error:
        print(json.dumps({"accepted": False, "error": type(error).__name__, "reason": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

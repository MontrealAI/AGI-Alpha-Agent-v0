# SPDX-License-Identifier: Apache-2.0
"""Execute fresh technical confirmation and independent matched-information checks."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from check_protocol import check
from independent_math import construct_graphs
from issue_seeds import verify_freeze


def permute(graph: list[list[int]], mapping: list[int]) -> list[list[int]]:
    """Relabel physical ports with a recorded old-to-new bijection."""
    out = [[0] * 16 for _ in range(16)]
    for i in range(16):
        for j in range(16):
            out[mapping[i]][mapping[j]] = graph[i][j]
    return out


def uncertainty(rng: random.Random) -> dict[str, Any]:
    """Generate a bounded box whose midpoint need not be the original nominal."""
    rate = rng.uniform(0.6, 1.8)
    half = rng.uniform(0.06, 0.22)
    leak = rng.uniform(0.04, 0.25)
    gain = rng.uniform(0.85, 1.15)
    return {"rate": [rate * (1 - half), rate * (1 + half)], "leak": [leak * 0.6, leak * 1.4],
            "gain": [gain * 0.95, gain * 1.05], "noise": rng.uniform(0.001, 0.008)}


def base_input(models: list[dict[str, Any]], ports: list[tuple[int, int]], rng: random.Random) -> dict[str, Any]:
    """Construct a fresh bounded JSON commissioning input."""
    return {"schema": "possibility-engine-input-v1", "models": models, "uncertainty": uncertainty(rng),
            "times": sorted({round(rng.uniform(0.04, 0.6), 6) for _ in range(31)}),
            "experiments": [{"actuator": a, "sensor": s, "cost_units": rng.randint(4, 25)} for a, s in ports],
            "failure_mode": "none"}


def cases(seed: int) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Create twenty-four binary and twelve meaningfully different portfolio tasks."""
    rng = random.Random(seed)
    witness = construct_graphs()
    graphs = [model["adjacency"] for model in witness["models"]]
    all_ports = [(a, s) for a in range(1, 16) for s in range(1, 16) if a != s]
    out = []
    for index in range(24):
        tail = list(range(1, 16))
        rng.shuffle(tail)
        mapping = [0] + tail
        models = [{"id": name, "adjacency": permute(graph, mapping)}
                  for name, graph in zip(("first", "second"), graphs)]
        mode = "joint" if index < 12 else ("actuator_only" if index < 15 else "sensor_only" if index < 18
                                           else "high_noise" if index < 20 else "identical" if index < 22 else "blocked")
        if mode == "actuator_only":
            ports = [(a, 0) for a in range(16)]
        elif mode == "sensor_only":
            ports = [(0, s) for s in range(16)]
        elif mode == "blocked":
            ports = rng.sample([(a, s) for a, s in all_ports
                                if models[0]["adjacency"][s][a] == models[1]["adjacency"][s][a]], 16)
        else:
            ports = rng.sample(all_ports, 16)
        data = base_input(models, ports, rng)
        if mode == "high_noise":
            data["uncertainty"]["noise"] = 0.2
        if mode == "identical":
            data["models"][1]["adjacency"] = copy.deepcopy(data["models"][0]["adjacency"])
        out.append((f"binary_{index:02d}_{mode}", data, {"case_family": "binary", "mode": mode,
                                                       "common_port_permutation": mapping}))
    neighbors = witness["root_neighbors"]
    other = [i for i in range(1, 16) if i not in neighbors]
    for index in range(12):
        models = []
        seen: set[str] = set()
        while len(models) < 6:
            new_neighbors, new_other = neighbors.copy(), other.copy()
            rng.shuffle(new_neighbors)
            rng.shuffle(new_other)
            mapping = list(range(16))
            for source, target in zip(neighbors + other, new_neighbors + new_other):
                mapping[source] = target
            graph = permute(graphs[len(models) % 2], mapping)
            signature = json.dumps(graph)
            if signature not in seen:
                seen.add(signature)
                models.append({"id": f"hypothesis_{len(models)}", "adjacency": graph})
        data = base_input(models, rng.sample(all_ports, 16), rng)
        data["failure_mode"] = ("none", "one_experiment", "one_terminal")[index % 3]
        out.append((f"successor_{index:02d}_{data['failure_mode']}", data,
                    {"case_family": "successor", "mode": data["failure_mode"],
                     "mission": "Identify one of six labeled networks with the declared failure tolerance"}))
    return out


def malformed_inputs(template: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Construct explicit invalid-input controls without drawing further randomness."""
    out = []
    for mode in ("asymmetric_graph", "nan_noise", "duplicate_ports", "zero_rate", "infinite_time", "boolean_cost"):
        data = copy.deepcopy(template)
        if mode == "asymmetric_graph":
            data["models"][0]["adjacency"][0][1] ^= 1
        elif mode == "nan_noise":
            data["uncertainty"]["noise"] = float("nan")
        elif mode == "duplicate_ports":
            data["experiments"].append(copy.deepcopy(data["experiments"][0]))
        elif mode == "zero_rate":
            data["uncertainty"]["rate"][0] = 0
        elif mode == "infinite_time":
            data["times"][0] = float("inf")
        else:
            data["experiments"][0]["cost_units"] = True
        out.append((f"invalid_{mode}", data))
    return out


def main() -> None:
    """Run the frozen CLI, preserve outcomes and independently check every delivery."""
    parser = argparse.ArgumentParser()
    parser.add_argument("freeze", type=Path)
    parser.add_argument("seeds", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verify_freeze(args.freeze)
    freeze_hash = hashlib.sha256(args.freeze.read_bytes()).hexdigest()
    seed_data = json.loads(args.seeds.read_text())
    if seed_data["freeze_sha256"] != freeze_hash:
        raise ValueError("Seed document is not bound to this source freeze")
    if args.output.exists():
        raise FileExistsError("Confirmation output already exists; preserve original outcomes")
    args.output.mkdir(parents=True)
    root = args.freeze.parent.resolve()
    library = args.output / "ordinary_library"
    copy_started = time.perf_counter()
    shutil.copytree(root / "src", library / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(root / "verification", library / "verification", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if (root / "evidence/development").exists():
        shutil.copytree(root / "evidence/development", library / "evidence/development")
    for document in ("README.md", "ACCEPTANCE.md"):
        if (root / document).exists():
            shutil.copy2(root / document, library / document)
    copy_seconds = time.perf_counter() - copy_started
    assert (library / "src/engine.py").read_bytes() == (root / "src/engine.py").read_bytes()
    library_files = [path for path in library.rglob("*") if path.is_file()]
    generated = cases(seed_data["technical_seed"])
    records = []
    for name, data, metadata in generated:
        directory = args.output / name
        directory.mkdir()
        input_path = directory / "input.json"
        input_path.write_text(json.dumps(data, indent=2) + "\n")
        (directory / "case.json").write_text(json.dumps(metadata, indent=2) + "\n")
        started = time.perf_counter()
        process = subprocess.run([sys.executable, str(root / "src/engine.py"), str(input_path),
                                  "--output", str(directory)], capture_output=True, text=True, timeout=45, check=False)
        elapsed = time.perf_counter() - started
        (directory / "stdout.txt").write_text(process.stdout)
        (directory / "stderr.txt").write_text(process.stderr)
        receipt: dict[str, Any] = {"name": name, **metadata, "cli_returncode": process.returncode,
                                   "cli_seconds": elapsed}
        try:
            if process.returncode != 0:
                raise RuntimeError("Primary CLI failed")
            result = json.loads((directory / "result.json").read_text())
            started = time.perf_counter()
            receipt.update(check(data, result))
            receipt["independent_seconds"] = time.perf_counter() - started
            receipt["primary_status"] = result["status"]
            receipt["selected_experiment_count"] = len(result["selected"])
            if metadata["case_family"] == "successor":
                library_directory = directory / "ordinary_library_delivery"
                started = time.perf_counter()
                comparison = subprocess.run(
                    [sys.executable, str((library / "src/engine.py").resolve()), str(input_path.resolve()),
                     "--output", str(library_directory.resolve())], cwd=library, capture_output=True,
                    text=True, timeout=45, check=False)
                receipt["ordinary_library_seconds"] = time.perf_counter() - started
                (directory / "ordinary_library_stdout.txt").write_text(comparison.stdout)
                (directory / "ordinary_library_stderr.txt").write_text(comparison.stderr)
                assert comparison.returncode == 0, "Ordinary-library execution failed"
                comparison_result = json.loads((library_directory / "result.json").read_text())
                assert comparison_result == result, "Ordinary-library complete semantic result differs"
                receipt["ordinary_library_exact_result_parity"] = True
        except Exception as error:
            receipt.update({"status": "fail", "error": f"{type(error).__name__}: {error}"})
        (directory / "independent_check.json").write_text(json.dumps(receipt, indent=2) + "\n")
        records.append(receipt)
        print(json.dumps({key: receipt[key] for key in ("name", "status", "cli_seconds")}), flush=True)
    for name, data in malformed_inputs(generated[0][1]):
        directory = args.output / name
        directory.mkdir()
        input_path = directory / "input.json"
        input_path.write_text(json.dumps(data, indent=2) + "\n")
        process = subprocess.run([sys.executable, str(root / "src/engine.py"), str(input_path),
                                  "--output", str(directory)], capture_output=True, text=True, timeout=45, check=False)
        (directory / "stdout.txt").write_text(process.stdout)
        (directory / "stderr.txt").write_text(process.stderr)
        receipt = {"name": name, "case_family": "malformed", "cli_returncode": process.returncode,
                   "status": "pass" if process.returncode != 0 and not (directory / "result.json").exists() else "fail"}
        records.append(receipt)
        (directory / "independent_check.json").write_text(json.dumps(receipt, indent=2) + "\n")
    verify_freeze(args.freeze)
    summary = {"schema": "possibility-engine-technical-confirmation-v1", "freeze_sha256": freeze_hash,
               "seed_file_sha256": hashlib.sha256(args.seeds.read_bytes()).hexdigest(),
               "cases": records, "passed": sum(row["status"] == "pass" for row in records),
               "failed": sum(row["status"] != "pass" for row in records), "source_unchanged": True,
               "ordinary_library_copy_seconds": copy_seconds,
               "ordinary_library_file_count": len(library_files),
               "ordinary_library_bytes": sum(path.stat().st_size for path in library_files),
               "ordinary_library_comparison_scope": "Same complete artifact library copied and run in isolated subprocess; portability, not retained advantage",
               "status": "pass" if all(row["status"] == "pass" for row in records) else "fail"}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("status", "passed", "failed", "source_unchanged")}), flush=True)
    if summary["failed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

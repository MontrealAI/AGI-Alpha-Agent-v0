# SPDX-License-Identifier: Apache-2.0
"""Independently execute generated RC netlists and preserve exact run receipts."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy.integrate import solve_ivp


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(token: str, parameters: dict[str, float]) -> float:
    expression = ast.parse(token.strip("{}"), mode="eval")

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id in parameters:
            return parameters[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -visit(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
        raise ValueError(f"Unsupported numeric expression: {token}")

    value = visit(expression)
    if not math.isfinite(value):
        raise ValueError("Nonfinite circuit value")
    return value


def parse_netlist(path: Path) -> dict[str, Any]:
    parameters: dict[str, float] = {}
    capacitors: list[tuple[str, float, float]] = []
    resistors: list[tuple[str, str, float]] = []
    readouts: dict[str, tuple[str, float]] = {}
    measurement: tuple[str, float] | None = None
    stop = 0.0
    names: set[str] = set()
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        fields = line.split()
        directive = fields[0].lower()
        if directive == ".param":
            for item in fields[1:]:
                name, raw_value = item.split("=", 1)
                parameters[name] = number(raw_value, parameters)
        elif directive in {".option", ".end"}:
            continue
        elif directive == ".tran":
            if fields[-1].lower() != "uic":
                raise ValueError("Initial-condition circuit must explicitly use uic")
            stop = number(fields[2], parameters)
        elif directive == ".measure":
            match = re.fullmatch(
                r"\.measure\s+tran\s+observation\s+FIND\s+v\(([A-Za-z][A-Za-z0-9_]*)\)\s+AT=(\S+)",
                line,
                re.IGNORECASE,
            )
            if not match or measurement is not None:
                raise ValueError("Unsupported or repeated measurement")
            measurement = (match[1], number(match[2], parameters))
        elif directive == "eread":
            if len(fields) != 6 or fields[2] != "0" or fields[4] != "0" or fields[1] in readouts:
                raise ValueError("Only an isolated grounded voltage-controlled readout is supported")
            readouts[fields[1]] = (fields[3], number(fields[5], parameters))
        elif directive.startswith("c"):
            if len(fields) != 5 or fields[2] != "0" or not fields[4].upper().startswith("IC="):
                raise ValueError("Only grounded capacitors with explicit IC are supported")
            capacitance = number(fields[3], parameters)
            initial = number(fields[4][3:], parameters)
            if capacitance <= 0 or fields[1] in names:
                raise ValueError("Nonpositive or repeated node capacitance")
            names.add(fields[1])
            capacitors.append((fields[1], capacitance, initial))
        elif directive.startswith("r"):
            if len(fields) != 4:
                raise ValueError("Malformed resistor")
            resistance = number(fields[3], parameters)
            if resistance <= 0:
                raise ValueError("Nonpositive resistance")
            resistors.append((fields[1], fields[2], resistance))
        else:
            raise ValueError(f"Unsupported circuit directive: {directive}")
    if not capacitors or measurement is None or not 0 < measurement[1] <= stop:
        raise ValueError("Missing or invalid circuit measurement")
    nodes = sorted(names, key=lambda item: int(item.removeprefix("n")))
    index = {node: position for position, node in enumerate(nodes)}
    measured_node, readout_gain = readouts.get(measurement[0], (measurement[0], 1.0))
    if measured_node not in index or any(node in index for node in readouts):
        raise ValueError("Measured node has no capacitor")
    capacitances = np.zeros(len(nodes))
    initial_values = np.zeros(len(nodes))
    conductance = np.zeros((len(nodes), len(nodes)))
    for node, capacitance, initial in capacitors:
        capacitances[index[node]] = capacitance
        initial_values[index[node]] = initial
    for left, right, resistance in resistors:
        value = 1.0 / resistance
        for node in (left, right):
            if node != "0" and node not in index:
                raise ValueError("Resistor node has no capacitor")
        if left != "0":
            conductance[index[left], index[left]] += value
        if right != "0":
            conductance[index[right], index[right]] += value
        if left != "0" and right != "0":
            conductance[index[left], index[right]] -= value
            conductance[index[right], index[left]] -= value
    return {
        "nodes": nodes,
        "capacitances": capacitances,
        "initial": initial_values,
        "conductance": conductance,
        "sensor_index": index[measured_node],
        "readout_gain": readout_gain,
        "observation_time": measurement[1],
        "stop_time": stop,
        "resistor_count": len(resistors),
        "parameters": parameters,
    }


def integrate_netlist(circuit: dict[str, Any]) -> dict[str, Any]:
    capacitances = circuit["capacitances"]
    conductance = circuit["conductance"]

    def derivative(_time: float, voltage: Any) -> Any:
        return -(conductance @ voltage) / capacitances

    result = solve_ivp(
        derivative,
        (0.0, circuit["observation_time"]),
        circuit["initial"],
        method="DOP853",
        t_eval=[circuit["observation_time"]],
        rtol=1e-11,
        atol=1e-13,
    )
    if not result.success:
        raise RuntimeError(result.message)
    return {
        "value": float(result.y[circuit["sensor_index"], -1]) * circuit["readout_gain"],
        "function_evaluations": result.nfev,
        "solver_success": bool(result.success),
        "solver_message": str(result.message),
    }


def expected_value(path: Path) -> tuple[float, Path, dict[str, Any]]:
    match = re.fullmatch(r"model_(\d+)_experiment_(\d+)\.cir", path.name)
    if not match:
        raise ValueError("Unexpected circuit filename")
    model, experiment = map(int, match.groups())
    result_path = path.parent / "result.json"
    result = json.loads(result_path.read_text())
    selected = next(item for item in result["selected"] if item["id"] == experiment)
    return float(selected["nominal_outputs"][model]), result_path, selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ngspice", type=Path)
    parser.add_argument("--library-dir", type=Path)
    args = parser.parse_args()
    acceptance_path = Path(__file__).with_name("CIRCUIT_ACCEPTANCE.json")
    acceptance = json.loads(acceptance_path.read_text())
    tolerance = float(acceptance["absolute_agreement_tolerance"])
    source_root = args.source_root.resolve()
    files = sorted(source_root.rglob("*.cir"))
    if not files:
        raise ValueError("No netlists found")
    args.output.mkdir(parents=True, exist_ok=False)
    bindings = []
    for path in files:
        expected, result_path, selected = expected_value(path)
        bindings.append(
            {
                "path": str(path.relative_to(source_root)),
                "sha256": digest(path),
                "result_sha256": digest(result_path),
                "expected_value": expected,
                "actuator": selected["actuator"],
                "sensor": selected["sensor"],
            }
        )
    freeze = {
        "schema": "possibility-circuit-freeze-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "checker_sha256": digest(Path(__file__)),
        "acceptance_sha256": digest(acceptance_path),
        "absolute_tolerance": tolerance,
        "source_root": str(source_root),
        "bindings": bindings,
    }
    (args.output / "pre_execution_freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
    env = os.environ.copy()
    if args.library_dir:
        env["LD_LIBRARY_PATH"] = str(args.library_dir.resolve())
    simulator: dict[str, Any] = {"status": "not_run"}
    if args.ngspice:
        version = subprocess.run(
            [str(args.ngspice.resolve()), "--version"], capture_output=True, text=True, timeout=30, env=env
        )
        simulator = {
            "binary_sha256": digest(args.ngspice),
            "version_returncode": version.returncode,
            "version_stdout": version.stdout,
            "version_stderr": version.stderr,
            "status": "available" if version.returncode == 0 else "unavailable",
        }
    records = []
    start = time.perf_counter()
    for path, binding in zip(files, bindings):
        receipt: dict[str, Any] = dict(binding)
        try:
            if digest(path) != binding["sha256"] or digest(path.parent / "result.json") != binding["result_sha256"]:
                raise ValueError("Source changed after pre-execution freeze")
            circuit = parse_netlist(path)
            result = integrate_netlist(circuit)
            ode_error = abs(result["value"] - binding["expected_value"])
            receipt.update(
                {
                    "nodes": len(circuit["nodes"]),
                    "resistors": circuit["resistor_count"],
                    "observation_time": circuit["observation_time"],
                    "ode": result,
                    "ode_absolute_error": ode_error,
                    "ode_pass": ode_error <= tolerance,
                }
            )
            if args.ngspice and simulator["status"] == "available":
                native = subprocess.run(
                    [str(args.ngspice.resolve()), "-n", "-b", str(path)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env,
                    cwd=args.output,
                )
                log_name = binding["path"].replace("/", "__") + ".log"
                log = {"returncode": native.returncode, "stdout": native.stdout, "stderr": native.stderr}
                (args.output / log_name).write_text(json.dumps(log, indent=2) + "\n")
                match = re.search(r"(?m)^observation\s*=\s*([+\-\d.eE]+)", native.stdout)
                if native.returncode != 0 or match is None:
                    raise RuntimeError(f"ngspice failed or omitted measurement; see {log_name}")
                value = float(match[1])
                native_error = abs(value - binding["expected_value"])
                cross_error = abs(value - result["value"])
                receipt.update(
                    {
                        "ngspice_value": value,
                        "ngspice_absolute_error": native_error,
                        "ngspice_ode_error": cross_error,
                        "ngspice_log": log_name,
                        "ngspice_pass": max(native_error, cross_error) <= tolerance,
                    }
                )
            receipt["status"] = "pass" if receipt["ode_pass"] and receipt.get("ngspice_pass", True) else "fail"
        except Exception as error:
            receipt.update({"status": "fail", "error": f"{type(error).__name__}: {error}"})
        records.append(receipt)
    summary = {
        "schema": "possibility-circuit-results-v1",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "simulator": simulator,
        "scope": acceptance["scope"],
        "source_imports": "No primary engine or response formula imported; Kirchhoff conductance stamping from netlists",
        "absolute_tolerance": tolerance,
        "cases": len(records),
        "passed": sum(item["status"] == "pass" for item in records),
        "failed": sum(item["status"] != "pass" for item in records),
        "elapsed_seconds": time.perf_counter() - start,
        "records": records,
    }
    (args.output / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: summary[key] for key in ("cases", "passed", "failed", "elapsed_seconds")}))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

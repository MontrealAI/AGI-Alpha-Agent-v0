# SPDX-License-Identifier: Apache-2.0
"""Check two frozen research-access inputs using the verified released package."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import time


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def conventional(problem: dict) -> tuple | None:
    """Exhaust all finite ordinary compositions with the identical declarations."""
    best = None
    for length in range(len(problem["steps"]) + 1):
        for sequence in itertools.permutations(problem["steps"], length):
            facts, cost, seconds, pending = set(problem["starting_facts"]), 0, 0, 0
            valid = True
            for step in sequence:
                if (
                    step["permission"] == "denied"
                    or not set(step["requires"]) <= facts
                    or not set(problem["obligations"]) <= set(step["preserves"])
                    or set(step["produces"]) <= facts
                ):
                    valid = False
                    break
                facts.update(step["produces"])
                cost += step["estimated_cost_micro_usd"]
                seconds += step["duration_seconds"]
                pending += step["permission"] == "required"
            if (
                valid
                and set(problem["required_outputs"]) <= facts
                and cost <= problem["cost_cap_micro_usd"]
                and seconds <= problem["seconds_cap"]
            ):
                rank = (pending, cost, seconds, tuple(step["step_id"] for step in sequence))
                if best is None or rank < best:
                    best = rank
    return best


def run(args: argparse.Namespace) -> None:
    proof = json.loads(args.publication_proof.read_bytes())
    assert args.confirm_released_execution and proof["release_published"] is True and proof["version"] == "1.47.0"
    assert len(proof["source_commit"]) == 40 and len(proof["wheel_sha256"]) == 64
    interpreter = args.installed_python.absolute()
    packages = list(interpreter.parents[1].glob("lib/python*/site-packages/alpha_factory_v1"))
    assert len(packages) == 1 and len(proof["runtime_sha256"]) == 75
    for path, expected in proof["runtime_sha256"].items():
        assert path.startswith("alpha_factory_v1/core/runtime/") and ".." not in Path(path).parts
        assert sha((packages[0].parent / path).read_bytes()) == expected, path
    source = args.source.resolve()
    freeze_data = (source / "FREEZE.json").read_bytes()
    freeze = json.loads(freeze_data)
    assert len(freeze["inputs"]) == 2
    args.output = args.output.absolute()
    args.output.mkdir(parents=True, exist_ok=False)
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code = """import json, sys
from alpha_factory_v1.core.runtime.successor.flywheel_access_path import AccessProblem, construct_access, check_access
problem = AccessProblem.model_validate_json(sys.stdin.buffer.read(120001))
result = construct_access(problem)
print(json.dumps({"result": result, "witness_checked": check_access(problem, result), "tampered_authority_checked": check_access(problem, {**result, "authority_granted": True})}, ensure_ascii=False, sort_keys=True))
"""
    results = []
    start = time.monotonic()
    for row in freeze["inputs"]:
        payload = (source / row["file"]).read_bytes()
        assert sha(payload) == row["sha256"]
        problem = json.loads(payload)
        assert problem["mission_id"] == row["id"] and problem["mode"] == "synthetic"
        elapsed = time.monotonic() - start
        assert elapsed < 45 and len(results) < 2
        before = time.monotonic()
        action = {
            "mission_id": row["id"],
            "input_sha256": row["sha256"],
            "status": "started",
            "exit_code": None,
            "wall_seconds": None,
            "stdout": "",
            "stderr": "",
        }
        results.append(action)

        def save_action() -> None:
            action["wall_seconds"] = time.monotonic() - before
            (args.output / "actions.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")

        save_action()
        try:
            process = subprocess.run(
                [str(interpreter), "-I", "-c", code],
                input=payload,
                cwd=args.output,
                env=env,
                capture_output=True,
                timeout=min(20, 45 - elapsed),
            )
        except subprocess.TimeoutExpired as error:

            def partial(value: bytes | str | None) -> str:
                return value.decode(errors="replace") if isinstance(value, bytes) else value or ""

            action.update(status="timeout", stdout=partial(error.stdout), stderr=partial(error.stderr))
            save_action()
            raise
        except OSError as error:
            action.update(status="spawn-failure", error_type=type(error).__name__)
            save_action()
            raise
        action.update(
            status="returned",
            exit_code=process.returncode,
            stdout=process.stdout.decode(),
            stderr=process.stderr.decode(),
        )
        save_action()
        assert process.returncode == 0, action
        value = json.loads(process.stdout)
        report = value["result"]
        assert report["status"] == row["expected_status"] and value["tampered_authority_checked"] is False
        assert report["authority_granted"] is False and report["customer_acceptance"] is False
        assert report["actual_experiment_performed"] is False and report["mission_id"] == row["id"]
        assert report["preserved_obligations"] == problem["obligations"]
        reference = conventional(problem)
        if reference is None:
            assert report["status"] == "no-plan" and report["steps"] == [] and value["witness_checked"] is False
        else:
            facts, cost, seconds, pending = set(problem["starting_facts"]), 0, 0, []
            declared = {step["step_id"]: step for step in problem["steps"]}
            for step in report["steps"]:
                assert step == declared[step["step_id"]] and step["permission"] != "denied"
                assert set(step["requires"]) <= facts and set(problem["obligations"]) <= set(step["preserves"])
                facts.update(step["produces"])
                cost += step["estimated_cost_micro_usd"]
                seconds += step["duration_seconds"]
                if step["permission"] == "required":
                    pending.append(step["step_id"])
            assert set(problem["required_outputs"]) <= facts
            assert cost <= problem["cost_cap_micro_usd"] and seconds <= problem["seconds_cap"]
            assert report["estimated_cost_micro_usd"] == cost and report["duration_seconds"] == seconds
            assert report["pending_permissions"] == pending and value["witness_checked"] is True
            assert reference == (len(pending), cost, seconds, tuple(step["step_id"] for step in report["steps"]))
        action["independent_comparator_rank"] = reference
        action["independent_original_constraints_checked"] = True
    elapsed = time.monotonic() - start
    assert elapsed <= 45
    result = {
        "schema": "released-research-package-canary-result/v1",
        "status": "passed",
        "publication": proof,
        "freeze_sha256": sha(freeze_data),
        "driver_sha256": sha(Path(__file__).read_bytes()),
        "actions": results,
        "aggregate_wall_seconds": elapsed,
        "actual_model_calls": 0,
        "actual_paid_api_usd": 0,
        "complete_actual_delivery_cost_usd": None,
        "actual_customer_collections_usd": 0,
        "source_mode": "synthetic",
        "library_execution_observed": True,
        "external_research_executed": False,
        "live_authentication": False,
        "frontier_handoff_qualified": False,
        "customer_acceptance": False,
        "retained_alpha": "not evaluated",
        "discovery_advantage": "not measured; equal-information conventional comparator",
    }
    (args.output / "RESULT.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "passed", "missions": len(results), "seconds": elapsed}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed-python", type=Path, required=True)
    parser.add_argument("--publication-proof", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-released-execution", action="store_true")
    run(parser.parse_args())

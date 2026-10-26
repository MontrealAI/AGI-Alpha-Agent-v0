# SPDX-License-Identifier: Apache-2.0
"""Replay the preserved development decision from a relocated source handoff."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--offline", action="store_true", help="Require already supplied wheel bytes.")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    start, cpu = time.perf_counter(), time.process_time()
    steps, decisions, plan_records = [], [], []
    error = None
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def execute(command: list[str], name: str) -> None:
        launched = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True, timeout=240, check=False)
        (out / f"{name}.stdout").write_text(result.stdout)
        (out / f"{name}.stderr").write_text(result.stderr)
        steps.append({"name": name, "command": command, "exit_code": result.returncode,
                      "wall_seconds": time.perf_counter() - launched})
        if result.returncode:
            raise ValueError("REPLAY_STEP_FAILED: " + name)

    try:
        for side, original_name in (
            ("before", "development-baseline-bridge"), ("after", "development-target")
        ):
            original = ROOT / "data" / f"{original_name}-plan.json"
            plan = json.loads(original.read_text())
            plan["native_lock"] = str(ROOT / "discovery/requirements/requirements-agent.lock")
            plan["incoming_constraint_metadata"] = [
                str(ROOT / "discovery/release-metadata/fastapi-0.141.1.json"),
                str(ROOT / "discovery/release-metadata/pydantic-settings-2.15.0.json"),
            ]
            plan["consumer_contract"] = str(ROOT / "protocol/component-contract.json")
            relocated = out / f"{side}-relocated-plan.json"
            relocated.write_text(json.dumps(plan, indent=2) + "\n")
            plan_records.append({"side": side, "original_path": str(original.relative_to(ROOT)),
                                 "original_sha256": digest(original), "relocated_sha256": digest(relocated),
                                 "change": "Local input path relocation only; package versions and native lock hash unchanged"})
            environment = out / f"{side}-environment"
            command = [sys.executable, str(ROOT / "curation/prepare_environment.py"), "--plan", str(relocated),
                       "--out", str(environment), "--metadata-reuse", str(ROOT / "publication/wheel-metadata")]
            for wheels in (ROOT / "data/development-baseline-bridge-environment/wheels",
                           ROOT / "data/development-target-environment/wheels", out / "before-environment/wheels"):
                if wheels.is_dir():
                    command += ["--wheel-reuse", str(wheels)]
            if args.offline:
                command.append("--offline")
            execute(command, side + "-setup")
            worker = ROOT / "src/manual_probe.py"
            consumer = ROOT / "data/consumer"
            contract = ROOT / "protocol/component-contract.json"
            observations = out / f"{side}-observations.json"
            python = environment / "venv/bin/python"
            binds = [worker, ROOT / "src/measured_run.py", consumer / "api.py", consumer / "models.py", contract,
                     ROOT / "protocol/component-projections.json", environment / "preparation.json",
                     environment / "requirements.lock", python]
            command = [sys.executable, str(ROOT / "src/measured_run.py"), "--phase", "relocated-" + side + "-probe",
                       "--record", str(out / f"{side}-execution.json"), "--timeout", "45"]
            for path in binds:
                command += ["--bind", str(path)]
            command += ["--output", str(observations), "--", str(python), "-I", "-B", str(worker),
                        "--consumer", str(consumer), "--contract", str(contract), "--out", str(observations)]
            execute(command, side + "-observations")
            verification = out / f"{side}-verification.json"
            verifier = ROOT / "src/verify_component.py"
            command = [sys.executable, str(ROOT / "src/measured_run.py"), "--phase", "relocated-" + side + "-verify",
                       "--record", str(out / f"{side}-verification-execution.json"), "--timeout", "45"]
            for path in [verifier, contract, observations, consumer / "api.py", consumer / "models.py",
                         ROOT / "protocol/component-projections.json", ROOT / "discovery/test_api_boundary.py",
                         environment / "preparation.json"]:
                command += ["--bind", str(path)]
            command += ["--output", str(verification), "--", sys.executable, str(verifier),
                        "--contract", str(contract), "--consumer", str(consumer), "--observations", str(observations),
                        "--environment", str(environment / "preparation.json"), "--projection",
                        "native-fastapi-bridge-v2", "--out", str(verification)]
            execute(command, side + "-verification")
            result = json.loads(verification.read_text())
            decisions.append({"side": side, "status": result["status"], "counts": result["counts"],
                              "verification_sha256": digest(verification)})
        if any(row["status"] != "PRESERVED_WITHIN_COMPONENT_CONTRACT" for row in decisions):
            raise ValueError("RECORDED_DEVELOPMENT_DISPOSITION_NOT_REPRODUCED")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {"schema": "relocated-first-delivery-replay/v1", "started_at": started_at,
              "ended_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "complete": error is None,
              "error": error, "script_sha256": digest(Path(__file__)), "source_root": str(ROOT),
              "offline": args.offline, "plan_relocations": plan_records, "steps": steps, "decisions": decisions,
              "wall_seconds": time.perf_counter() - start, "process_cpu_seconds": time.process_time() - cpu,
              "child_cpu_seconds": children.ru_utime + children.ru_stime, "money_usd": None,
              "mission_count_increment": 0, "role": "Replay of exposed development; not fresh confirmation or a new job"}
    (out / "replay.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("complete", "error", "decisions", "wall_seconds")}))
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

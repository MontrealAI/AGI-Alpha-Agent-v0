# SPDX-License-Identifier: Apache-2.0
"""Packaging-only controls on synthetic copies; never a primary mission result.

Rebased receipts are deliberately synthetic test inputs, not new execution
attestations. The optional semantic control invokes only the independent verifier
on one altered observation; it does not execute or discover a dependency defect.
"""

import argparse
import ast
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")


def refresh_manifest(pair):
    file = pair / "pair.json"
    data = read(file)
    for entry in data["artifacts"]:
        path = pair / entry["path"]
        if path.is_file():
            entry.update(sha256=sha(path), bytes=path.stat().st_size)
    write(file, data)


def relocated_fixture(original, pair):
    shutil.copytree(original, pair)

    def rebase(item):
        if isinstance(item, dict):
            copied = {key: rebase(value) for key, value in item.items()}
            if isinstance(copied.get("path"), str):
                old = Path(copied["path"])
                if old.is_absolute() and old.is_relative_to(original):
                    copied["path"] = str(pair / old.relative_to(original))
                path = Path(copied["path"])
                if path.is_file() and {"sha256", "bytes"}.issubset(copied):
                    copied.update(sha256=sha(path), bytes=path.stat().st_size)
            return copied
        if isinstance(item, list):
            return [rebase(value) for value in item]
        return item

    for side in ("before", "after"):
        for kind in ("execution", "verification-execution"):
            path = pair / f"{side}-{kind}.json"
            data = rebase(read(path))
            data["synthetic_control_only"] = True
            data["control_note"] = "Relocated copy for parser/decision controls; not a new consumer execution receipt."
            write(path, data)
    refresh_manifest(pair)


def mutate_receipt(pair, kind, change, side="after"):
    path = pair / f"{side}-{kind}.json"
    data = read(path)
    change(data)
    write(path, data)
    refresh_manifest(pair)


def unbind(data):
    data["input_identities_before"] = []
    data["input_identities_after"] = []


def stale_verifier(data):
    for field in ("input_identities_before", "input_identities_after"):
        for item in data[field]:
            if Path(item["path"]).name == "verify_component.py":
                item["sha256"] = "0" * 64


def wrong_output(data):
    for item in data["output_identities"]:
        item["path"] = "/not-the-executed-output/observations.json"


def change_pair(pair, key, value):
    path = pair / "pair.json"
    data = read(path)
    data[key] = value
    write(path, data)


def wrong_job(pair):
    path = pair / "job.json"
    data = read(path)
    data["consumer"]["api_sha256"] = "0" * 64
    write(path, data)
    change_pair(pair, "job_sha256", sha(path))
    refresh_manifest(pair)


def missing_manifest_entry(pair):
    path = pair / "pair.json"
    data = read(path)
    data["artifacts"] = [row for row in data["artifacts"] if row["path"] != "after-execution.json"]
    write(path, data)


def custody_predicate(controller_path, pair):
    tree = ast.parse(controller_path.read_text())
    assignment = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == "result"
            and isinstance(target.slice, ast.Constant)
            and target.slice.value == "custody_complete"
            for target in node.targets
        )
    )
    generator = assignment.value.args[0]
    with_field = isinstance(generator.generators[0].target, ast.Tuple)
    records = []
    for side in ("before", "after"):
        for field, filename in [("execution", "execution"), ("verification_execution", "verification-execution")]:
            item = read(pair / f"{side}-{filename}.json")
            if side == "after" and field == "verification_execution":
                item["exit_code"] = 2
            records.append((field, item) if with_field else item)
    expression = compile(ast.Expression(body=assignment.value), str(controller_path), "eval")
    return eval(expression, {"records": records}), assignment.lineno


def semantic_fixture(pair, job_path, controller):
    observed = pair / "after-observations.json"
    data = read(observed)
    next(row for row in data["observations"] if row["id"] == "asgi.missing-length")["observation"]["status"] = 400
    data["synthetic_control_only"] = True
    data["control_note"] = "One deliberately wrong observed status; not an observed upstream dependency regression."
    write(observed, data)
    # The producer receipt remains an explicitly synthetic fixture; only the
    # independent verifier below is actually executed for this control.
    producer = read(pair / "after-execution.json")
    for item in producer["output_identities"]:
        if Path(item["path"]) == observed:
            item.update(sha256=sha(observed), bytes=observed.stat().st_size)
    write(pair / "after-execution.json", producer)
    job = read(job_path)
    environment = ROOT / job["after"]["environment"]
    contract = ROOT / job["contract"]["path"]
    consumer = ROOT / job["consumer"]["directory"]
    verified = pair / "after-verification.json"
    receipt = pair / "after-verification-execution.json"
    for path in [verified, receipt, receipt.with_suffix(".stdout.txt"), receipt.with_suffix(".stderr.txt")]:
        if path.exists():
            path.unlink()
    binds = [
        job_path,
        ROOT / "src/verify_component.py",
        contract,
        ROOT / "protocol/component-projections.json",
        observed,
        consumer / "api.py",
        consumer / "models.py",
        ROOT / "discovery/test_api_boundary.py",
        environment / "preparation.json",
    ]
    command = [
        sys.executable,
        str(ROOT / "src/measured_run.py"),
        "--phase",
        "synthetic-semantic-fault-verification",
        "--record",
        str(receipt),
        "--timeout",
        "45",
    ]
    for path in binds:
        command.extend(["--bind", str(path)])
    command.extend(
        [
            "--output",
            str(verified),
            "--",
            sys.executable,
            str(ROOT / "src/verify_component.py"),
            "--contract",
            str(contract),
            "--consumer",
            str(consumer),
            "--environment",
            str(environment / "preparation.json"),
            "--projection",
            "native-fastapi-bridge-v2",
            "--observations",
            str(observed),
            "--out",
            str(verified),
        ]
    )
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    custody, _ = custody_predicate(controller, pair)
    change_pair(pair, "custody_complete", custody)
    refresh_manifest(pair)
    return {
        "verifier_wrapper_exit": result.returncode,
        "verifier_child_exit": read(receipt)["exit_code"],
        "verifier_status": read(verified)["status"],
        "custody_complete": custody,
        "consumer_executed_for_control": False,
        "producer_observation_is_synthetic": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=ROOT / "src/package_component.py")
    parser.add_argument("--controller", type=Path, default=ROOT / "src/run_pair.py")
    parser.add_argument("--pair", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--semantic-control", action="store_true")
    args = parser.parse_args()
    args.pair = args.pair.resolve()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=False)
    start, cpu = time.perf_counter(), time.process_time()
    pins = {str(path): sha(path) for path in (args.candidate, args.controller, ROOT / "src/conventional_package.py")}
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location("isolated_candidate_review", args.candidate)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    receipt = read(args.pair / "before-execution.json")
    job_sha = read(args.pair / "pair.json")["job_sha256"]
    job_path = next(
        Path(row["path"])
        for row in receipt["input_identities_before"]
        if row["sha256"] == job_sha and Path(row["path"]).is_file()
    )
    scenarios = [
        ("valid-relocated-fixture", None, True),
        ("missing-execution-prebindings", lambda p: mutate_receipt(p, "execution", unbind), False),
        ("stale-verifier-source-binding", lambda p: mutate_receipt(p, "verification-execution", stale_verifier), False),
        ("wrong-output-path-matching-hash", lambda p: mutate_receipt(p, "execution", wrong_output), False),
        ("stale-pair-worker-hash", lambda p: change_pair(p, "worker_sha256", "0" * 64), False),
        ("wrong-job-consumer-hash", wrong_job, False),
        ("wrong-pair-arm", lambda p: change_pair(p, "arm", "conventional"), False),
        ("missing-required-manifest-entry", missing_manifest_entry, False),
        (
            "unstarted-command",
            lambda p: mutate_receipt(p, "execution", lambda d: d.update(command_started=False)),
            False,
        ),
        ("boolean-exit-code", lambda p: mutate_receipt(p, "execution", lambda d: d.update(exit_code=True)), False),
        ("missing-observation", lambda p: (p / "after-observations.json").unlink(), False),
        (
            "tampered-observation-unrefreshed-hash",
            lambda p: (p / "after-observations.json").write_text((p / "after-observations.json").read_text() + " "),
            False,
        ),
    ]
    rows = []
    for name, mutate, expected in scenarios:
        directory = args.out / name
        pair = directory / "pair"
        relocated_fixture(args.pair, pair)
        (directory / "CONTROL-NOT-EXPERIMENT.md").write_text(__doc__ + "\n")
        if mutate:
            mutate(pair)
        selected_job = pair / "job.json" if name == "wrong-job-consumer-hash" else job_path
        try:
            packet = module.assemble(selected_job, pair, directory / "package")
            actual = {
                "decision": packet["decision"],
                "accepted": packet["useful_outcome_accepted"],
                "custody_failures": packet["custody_failures"],
                "error": None,
            }
        except Exception as exc:
            actual = {
                "decision": None,
                "accepted": False,
                "custody_failures": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
        rows.append(
            {
                "id": name,
                "synthetic_control_only": True,
                "expected_accepted": expected,
                **actual,
                "control_passed": actual["accepted"] == expected,
            }
        )
    custody, line = custody_predicate(args.controller, args.pair)
    rows.append(
        {
            "id": "verified-regression-exit-two-custody",
            "synthetic_control_only": True,
            "expected_custody_complete": True,
            "actual_custody_complete": custody,
            "source_line": line,
            "control_passed": custody is True,
        }
    )
    if args.semantic_control:
        directory = args.out / "synthetic-semantic-fault"
        pair = directory / "pair"
        relocated_fixture(args.pair, pair)
        (directory / "CONTROL-NOT-EXPERIMENT.md").write_text(__doc__ + "\n")
        outcome = semantic_fixture(pair, job_path, args.controller)
        packet = module.assemble(job_path, pair, directory / "package")
        rows.append(
            {
                "id": "synthetic-semantic-fault-through-real-verifier",
                "synthetic_control_only": True,
                **outcome,
                "decision": packet["decision"],
                "custody_failures": packet["custody_failures"],
                "control_passed": outcome["verifier_child_exit"] == 2
                and outcome["verifier_status"] == "BEHAVIOR_MISMATCH"
                and packet["decision"] == "COMPONENT_REGRESSION"
                and not packet["custody_failures"],
            }
        )
    report = {
        "schema": "independent-retained-custody-controls/v2",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_sha256_before": pins,
        "source_sha256_after": {path: sha(Path(path)) for path in pins},
        "source_pair_sha256": sha(args.pair / "pair.json"),
        "scope": __doc__,
        "consumer_execution": False,
        "primary_input_reads": False,
        "controls": rows,
        "passed": sum(row["control_passed"] for row in rows),
        "total": len(rows),
        "wall_seconds": time.perf_counter() - start,
        "process_cpu_seconds": time.process_time() - cpu,
        "money_usd": None,
    }
    write(args.out / "controls.json", report)
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "total": report["total"],
                "out": str(args.out),
                "failures": [row for row in rows if not row["control_passed"]],
                "wall_seconds": report["wall_seconds"],
                "process_cpu_seconds": report["process_cpu_seconds"],
            }
        )
    )
    raise SystemExit(
        0
        if report["passed"] == report["total"] and report["source_sha256_before"] == report["source_sha256_after"]
        else 1
    )


if __name__ == "__main__":
    main()

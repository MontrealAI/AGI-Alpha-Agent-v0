# SPDX-License-Identifier: Apache-2.0
"""Preregister then execute finite source-operation continuity and load qualification."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.campaign_operation import CampaignOperation, OperationSpec, example
from alpha_factory_v1.core.runtime.successor.protocol import canonical
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

NAMESPACE = uuid.UUID("78f6dfbd-70a8-4dfa-8cb5-759a5b8c43d9")
WORKER = """
import os, signal, sys
from pathlib import Path
from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor.campaign_operation import CampaignOperation, OperationSpec
from alpha_factory_v1.core.runtime.successor.transport import read_document
spec = OperationSpec.model_validate(read_document(Path(sys.argv[1])))
operation = CampaignOperation(Journal.initialize(Path(sys.argv[2])))
operation.start(spec)
original = operation.experiment._campaign
def fault(*args):
    result = original(*args)
    if sys.argv[3] == 'crash':
        os.kill(os.getpid(), signal.SIGKILL)
    if sys.argv[3] == 'stop':
        operation.stop(spec.operation_id)
    return result
operation.experiment._campaign = fault
operation.run(spec.operation_id)
"""


def write(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def configuration(name: str, training: int, confirmation: int, horizon: int, timed: bool) -> OperationSpec:
    raw = example().model_dump()
    templates = [*raw["training"], *raw["confirmation"]]
    raw["operation_id"] = str(uuid.uuid5(NAMESPACE, name + "-operation"))
    raw["study"]["study_id"] = str(uuid.uuid5(NAMESPACE, name + "-study"))
    raw["accountable_operator"] = "Codex bounded qualification controller; human labor unmeasured"
    raw["study"]["terminal_campaigns"] = confirmation
    raw["horizon_seconds"] = horizon
    raw["training"], raw["confirmation"] = [], []
    for index in range(training + confirmation):
        item = copy.deepcopy(templates[index % len(templates)])
        label = name + "-unit-" + str(index)
        item["after_ms"] = index * 4000 if timed else 0
        item["unit"]["unit_id"] = label
        item["unit"]["request"]["campaign_id"] = str(uuid.uuid5(NAMESPACE, label))
        for part, documents in (
            ("development", item["unit"]["request"]["development"]),
            ("fresh", item["unit"]["terminal"]),
        ):
            for document in documents:
                document["title"] = "Synthetic " + label + " " + part
                for claim in document["claims"]:
                    claim["text"] = "Constructed " + label + " " + part + ": " + claim["text"]
        raw["training" if index < training else "confirmation"].append(item)
    return OperationSpec.model_validate(raw)


def prepare(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    declarations = [
        ("continuous", 1, 3, 60, True),
        ("active-stop", 1, 3, 60, True),
        ("load-4", 1, 3, 60, False),
        ("load-8", 2, 6, 60, False),
        ("load-10", 2, 8, 60, False),
        ("deadline-10", 2, 8, 1, False),
    ]
    hashes = {}
    for name, training, confirmation, horizon, timed in declarations:
        spec = configuration(name, training, confirmation, horizon, timed)
        data = canonical(spec.model_dump())
        path = destination / (name + ".json")
        path.write_bytes(data)
        hashes[path.name] = hashlib.sha256(data).hexdigest()
    import alpha_factory_v1.core.runtime.successor.campaign_operation as operation_module
    import alpha_factory_v1.core.runtime.successor.campaign_experiment as study_module
    import alpha_factory_v1.core.runtime.successor.transformation as selector_module

    write(
        destination / "preregister.json",
        {
            "schema": "source-operation-qualification-plan/v1",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "workloads_sha256": hashes,
            "runtime_sources": {
                module.__name__: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
                for module in (operation_module, study_module, selector_module)
            },
            "maximum_campaign_seconds": 60,
            "workload_fixed_before_execution": True,
            "fault": "SIGKILL after first child commits, before parent attachment; one restart through unchanged CLI",
            "stop": "permanent operation-stop during first child handoff; stale handoff must fail",
            "load": "4, 8 and 10 whole units, three policies, concurrency one; separate 1-second 10-unit deadline case",
            "claim": "synthetic local mechanism only; same operator; no independent custody or commercial outcome",
            "human_effort": "Setup/engineering/review minutes unmeasured; fault controller and restart disclosed.",
        },
    )


def invoke(command: list[str], output: Path, timeout: int = 90) -> int:
    with output.open("xb") as stream:
        return subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, check=False).returncode


def execute(plan: Path, destination: Path) -> None:
    if os.name != "posix":
        raise ValueError("this SIGKILL qualification harness requires a POSIX reference host")
    frozen = json.loads((plan / "preregister.json").read_text())
    for name, expected in frozen["workloads_sha256"].items():
        if hashlib.sha256((plan / name).read_bytes()).hexdigest() != expected:
            raise ValueError("preregistered workload changed")
    import alpha_factory_v1.core.runtime.successor.campaign_operation as operation_module
    import alpha_factory_v1.core.runtime.successor.campaign_experiment as study_module
    import alpha_factory_v1.core.runtime.successor.transformation as selector_module

    for module in (operation_module, study_module, selector_module):
        if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != frozen["runtime_sources"][module.__name__]:
            raise ValueError("frozen runtime source changed")
    destination.mkdir(parents=True, exist_ok=False)
    summaries = []
    for filename in frozen["workloads_sha256"]:
        name = Path(filename).stem
        config = plan / filename
        spec = OperationSpec.model_validate_json(config.read_bytes())
        case = destination / name
        case.mkdir()
        home = case / "private-home"
        started = time.monotonic_ns()
        mode = "crash" if name == "continuous" else "stop" if name == "active-stop" else "none"
        first_exit = invoke(
            [sys.executable, "-c", WORKER, str(config.resolve()), str(home.resolve()), mode], case / "first-process.log"
        )
        operation = CampaignOperation(Journal(home))
        recovered_digest = None
        recovery_exit = None
        if mode == "crash":
            parent = operation.experiment.show(spec.study.study_id)
            child_id = parent["training"]["planned_campaigns"][0]["campaign_id"]
            before = operation.experiment.loop.show(child_id)
            if first_exit != -9 or before["state"] != "completed" or parent["training"]["runs"]:
                raise AssertionError("fault missed the declared committed-child handoff")
            recovery_exit = invoke(
                [
                    sys.executable,
                    "-m",
                    "alpha_factory_v1.core.runtime.cli",
                    "--home",
                    str(home.resolve()),
                    "successor-study",
                    "--output",
                    str((case / "resumed-status.json").resolve()),
                    "operation-run",
                    spec.operation_id,
                ],
                case / "recovery-process.log",
            )
            operation = CampaignOperation(Journal(home))
            after = operation.experiment.loop.show(child_id)
            if after["digest"] != before["digest"] or after["revision"] != before["revision"]:
                raise AssertionError("restart repeated the committed measurement")
            recovered_digest = after["digest"]
        exported = operation.export(spec.operation_id)
        write(case / "public-history.json", exported)
        write(case / "journal-verification.json", operation.journal.verify())
        state = exported["status"]["state"]
        if name == "continuous" and (state != "completed" or recovery_exit != 0):
            raise AssertionError("predefined continuous campaign failed")
        if name == "active-stop" and state != "canceled":
            raise AssertionError("active stop did not cancel")
        summaries.append(
            {
                "case": name,
                "first_process_exit": first_exit,
                "recovery_process_exit": recovery_exit,
                "wall_ns_including_process_launch": time.monotonic_ns() - started,
                "reconciled_original_child_digest": recovered_digest,
                "status": exported["status"],
                "study_freeze": exported["evidence"]["study"]["freeze"],
                "confirmation": {
                    key: value
                    for key, value in (exported["evidence"]["study"].get("confirmation") or {}).items()
                    if key not in {"units", "planned_campaigns"}
                },
            }
        )
    write(
        destination / "summary.json",
        {
            "schema": "source-operation-qualification-results/v1",
            "plan_sha256": hashlib.sha256((plan / "preregister.json").read_bytes()).hexdigest(),
            "cases": summaries,
            "unattended_process_left_running": False,
            "general_growth_claim": False,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.plan)
    elif args.output is None:
        parser.error("run requires --output")
    else:
        execute(args.plan, args.output)


if __name__ == "__main__":
    main()

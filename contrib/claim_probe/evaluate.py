# SPDX-License-Identifier: Apache-2.0
"""Source-frozen paired evaluation with complete denominators and raw receipts."""

import collections
import hashlib
import json
import secrets
import sys
import time
from pathlib import Path

from alpha_factory_v1.core.runtime.claim_probe import checker, instrument
from contrib.claim_probe.comparators import grid_ablation, ordinary_library
from contrib.claim_probe.generate import FAMILIES, make_task


def evaluate(mode, directory):
    if mode not in {"training", "confirmation"}:
        raise ValueError("evaluation mode")
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[2]
    paths = sorted((source / "alpha_factory_v1/core/runtime/claim_probe").glob("*.py"))
    paths += sorted(Path(__file__).parent.glob("*.py"))
    paths += [
        source.parent / "PROTOCOL.md",
        source / "alpha_factory_v1/core/runtime/cli.py",
        source / "pyproject.toml",
        source / "alpha_factory_v1/core/runtime/meta_discovery/exchange.py",
    ]
    hashes = {str(p.relative_to(source.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    freeze = {
        "sourceHashes": hashes,
        "endpoints": ["accepted", "decisive", "status", "falseClaim", "CPUSeconds", "wallSeconds"],
        "families": FAMILIES,
        "instancesPerFamily": 12 if mode == "confirmation" else 3,
        "mode": mode,
    }
    (out / "freeze.json").write_text(json.dumps(freeze, sort_keys=True, indent=2) + "\n")
    freeze_hash = hashlib.sha256((out / "freeze.json").read_bytes()).hexdigest()
    seed = secrets.randbits(48) if mode == "confirmation" else 20261028
    (out / "freshness.json").write_text(
        json.dumps(
            {
                "freezeSha256": freeze_hash,
                "seedGeneratedAfterFreeze": True,
                "seed": seed,
                "seedGeneratedUTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "concealedFromConstruction": False,
            },
            indent=2,
        )
        + "\n"
    )
    rows = []
    for fi, family in enumerate(FAMILIES):
        for i in range(freeze["instancesPerFamily"]):
            task = make_task(seed + fi * 1000 + i, family, i)
            arms = {}
            for name, fn in [("instrument", instrument.probe), ("ordinary_library", ordinary_library)]:
                cpu = time.process_time()
                wall = time.monotonic()
                try:
                    result = fn(task)
                    validation = checker.check(task, result)
                    arms[name] = {
                        "result": result,
                        "check": validation,
                        "CPUSeconds": time.process_time() - cpu,
                        "wallSeconds": time.monotonic() - wall,
                    }
                except Exception as error:
                    arms[name] = {
                        "error": type(error).__name__ + ": " + str(error),
                        "CPUSeconds": time.process_time() - cpu,
                        "wallSeconds": time.monotonic() - wall,
                    }
            expected = checker.globally_nonnegative(*checker.validate(task))
            for arm in arms.values():
                status = arm.get("result", {}).get("status", "ERROR")
                arm["falseClaim"] = (status == "PROVED" and not expected) or (status == "REFUTED" and expected)
            rows.append(
                {
                    "task": task,
                    "family": family,
                    "arms": arms,
                    "referenceNonnegative": expected,
                    "gridAblation": grid_ablation(task),
                }
            )
    with (out / "tasks.jsonl").open("x") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    summaries = {}
    for name in ["instrument", "ordinary_library"]:
        summaries[name] = {
            "statuses": dict(
                collections.Counter(x["arms"][name].get("result", {}).get("status", "ERROR") for x in rows)
            ),
            "accepted": sum(x["arms"][name].get("check", {}).get("accepted", False) for x in rows),
            "decisive": sum(x["arms"][name].get("check", {}).get("decisive", False) for x in rows),
            "falseClaims": sum(x["arms"][name]["falseClaim"] for x in rows),
            "CPUSeconds": sum(x["arms"][name]["CPUSeconds"] for x in rows),
        }
    summary = {
        "mode": mode,
        "tasks": len(rows),
        "freezeSha256": freeze_hash,
        "seed": seed,
        "arms": summaries,
        "scope": "Authored exact polynomial tasks; source-grounded bridge separate; not frontier-model or empirical discovery evidence",
        "independentModelArms": "NOT RUN",
        "allFailuresRetained": True,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    evaluate(sys.argv[1], sys.argv[2])

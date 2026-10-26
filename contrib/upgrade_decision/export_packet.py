# SPDX-License-Identifier: Apache-2.0
"""One-shot inert evidence export; no journal, credential, server or operator grant."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import component, core
from .delivery import HERE, accounting, package
from .worker import UpgradeDecisionWorker


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=HERE / "examples/catalog.json")
    parser.add_argument("--case", default="native-component-refresh-development")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("use a new output file; original packets are never overwritten")
    started, cpu = time.perf_counter_ns(), time.process_time_ns()
    node, git = shutil.which("node"), shutil.which("git")
    if node is None or git is None:
        parser.error("the existing Node/Git tooling is unavailable")
    worker = UpgradeDecisionWorker(args.catalog, python=Path(sys.executable), node=Path(node), git=Path(git))
    selection = worker.prepare_input(args.case)
    pack = core.load(worker._selection(selection))
    record = component.assess(pack) if pack["schema"] == component.SCHEMA else core.assess(pack)
    record["implementation"] = worker.source_record()
    costs, ledger = accounting(record)
    result = subprocess.run(
        [node, "--max-old-space-size=128", str(HERE / "costs.mjs")],
        input=core.canonical({"accounting": costs, "ledger": ledger}),
        capture_output=True,
        timeout=10,
        check=True,
    )
    analysis = core.load(result.stdout)
    worker._sources()
    bundle = package(record, pack, costs, ledger, analysis, notices=(HERE / "NOTICES.md").read_bytes())
    with args.output.open("xb") as stream:
        stream.write(bundle)
    print(
        json.dumps(
            {
                "output": str(args.output.absolute()),
                "sha256": core.sha(bundle),
                "bytes": len(bundle),
                "nextAction": record["nextAction"],
                "elapsedNs": time.perf_counter_ns() - started,
                "parentCpuNs": time.process_time_ns() - cpu,
                "scope": "One-shot inert evidence export; no connected execution, journal history or operator adoption is claimed. Complete monetary and attention costs remain unknown.",
            }
        )
    )


if __name__ == "__main__":
    main()

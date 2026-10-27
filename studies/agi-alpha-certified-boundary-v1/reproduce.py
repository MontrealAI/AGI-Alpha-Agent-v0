# SPDX-License-Identifier: Apache-2.0
"""Reproduce the fixed research results without modifying preserved evidence.

Default verification uses only Python's standard library. Optional native
ecosystem execution requires the pinned dependencies in requirements-native.txt.
Numerical rediscovery is separate and is not required to verify the theorem.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent


def main() -> int:
    """Run both proof constructions and independent financial reconciliation."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reproduction_results"))
    parser.add_argument("--native", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or sys.flags.optimize:
        print("Choose a fresh output directory and run without -O.", file=sys.stderr)
        return 2
    output.mkdir(parents=True)
    results = []
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="replay_", dir=output) as temporary:
        work = Path(temporary)
        # Copy bounded study artifacts, not publication PDFs or prior copyrighted sources.
        for name in ("scout", "study", "lineage", "fresh_conventional", "certificate", "economics"):
            source = ROOT / name
            for path in source.rglob("*"):
                if not path.is_file() or path.suffix in (".pdf", ".txt", ".html", ".pyc"):
                    continue
                if "capacity_prior_art" in path.parts or "__pycache__" in path.parts:
                    continue
                destination = work / path.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
        for name in ("certificate_service.py", "final_certificate.py"):
            shutil.copyfile(ROOT / name, work / name)
        commands = [
            ["final_certificate.py", "--request", "study/final_request.json", "--output", "final_check"],
            ["certificate_service.py", "--request", "study/accepted_request.json", "--output", "polynomial_check"],
            ["economics/model.py"], ["economics/audit.py"], ["lineage/economic_replay.py"],
        ]
        if (work / "economics/value_pricing.py").exists():
            commands.append(["economics/value_pricing.py"])
        if args.native:
            commands.append(["lineage/native/integration/native_bridge.py", "--input",
                             "lineage/native/final_weight_metadata.json", "--output", "native_check"])
        for index, command in enumerate(commands):
            begin = time.monotonic()
            process = subprocess.run([sys.executable, "-E", "-B", *command], cwd=work,
                                     capture_output=True, text=True, timeout=120, check=False)
            log = output / f"step_{index + 1}.log"
            log.write_text(process.stdout + process.stderr)
            results.append({"command": command, "exit_code": process.returncode,
                            "elapsed_seconds": time.monotonic() - begin,
                            "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
            if process.returncode:
                print(process.stderr[-2000:], file=sys.stderr)
                (output / "FAILURE.json").write_text(json.dumps(results, indent=2) + "\n")
                return 1
        for relative in ("final_check", "polynomial_check", "native_check"):
            if (work / relative).exists():
                shutil.copytree(work / relative, output / relative)
        for relative in ("economics/results.json", "economics/audit.json", "lineage/ECONOMIC_REPLAY.json",
                         "economics/scenarios.csv", "economics/cost_detail.csv", "economics/cash_ledger.csv",
                         "economics/fee_participation_grid.csv", "economics/conditional_participation_discounts.csv",
                         "economics/arrangements.csv", "economics/value_pricing_grid.csv",
                         "economics/value_pricing_audit.json"):
            shutil.copyfile(work / relative, output / Path(relative).name)
    report = {"status": "PASS: fixed certificates and accounting reconciled",
              "executed_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.version, "executions": results,
              "elapsed_seconds": time.monotonic() - started, "native_reproduced": args.native,
              "claims": {"final_heft_lower_bound": "17902560/18258529", "relation": ">=",
                         "actual_revenue": 0, "actual_complete_profit": None,
                         "conditional_central_full_project_profit_usd": 2408,
                         "exclusive_operational_or_discovery_alpha_established": False}}
    (output / "REPRODUCTION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

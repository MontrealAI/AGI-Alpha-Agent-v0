# SPDX-License-Identifier: Apache-2.0
"""Replay frozen scientific and commercial evidence without issuing new seeds."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .confirm import technical, verify_freeze
from .operate import evaluate
from .verify import audit_path


def replay(freeze: Path, seeds: Path, records: Path, output: Path, full: bool = False) -> dict[str, Any]:
    verify_freeze(freeze)
    if output.exists():
        raise ValueError("Replay output must be a new directory.")
    output.mkdir(parents=True)
    technical_result = technical(freeze, seeds, output / "technical")
    audit = audit_path(records)
    result: dict[str, Any] = {"technical": technical_result, "original_records_audit": audit,
                              "mode": "reproduction, not fresh confirmation",
                              "timing_boundary": "CPU timings and fresh native signatures need not be byte-identical."}
    if full:
        root = Path(__file__).resolve().parent
        protocol = json.loads((root / "protocol.json").read_text())
        policy = json.loads((root / "policy.json").read_text())
        issued = json.loads(seeds.read_text())
        result["economy"] = evaluate(output / "economy", issued["scenarios"], protocol, policy)
        result["replayed_records_audit"] = audit_path(output / "economy")
    (output / "replay-receipt.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    result = replay(args.freeze, args.seeds, args.records, args.output, args.full)
    print(json.dumps({"mode": result["mode"], "records_audit_passed": result["original_records_audit"]["passed"]}))
    passed = result["original_records_audit"]["passed"] and result["technical"]["passed"]
    if args.full:
        passed = passed and result["replayed_records_audit"]["passed"]
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

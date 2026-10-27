# SPDX-License-Identifier: Apache-2.0
"""Replay modeled scenario amounts through the unchanged native accounting boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bridge import replay_native
from bundle import regular_bytes, sha256


def run(commands_path: Path, output: Path) -> dict[str, Any]:
    """Preserve the modeled money label while exercising real signed local code."""
    if output.exists():
        raise ValueError("new accounting evidence path required")
    raw = regular_bytes(commands_path)
    supplied = json.loads(raw)
    commands = supplied.get("commands") if isinstance(supplied, dict) else supplied
    if not isinstance(commands, list):
        raise ValueError("model ledger requires a list of declared commands")
    replay = replay_native(commands, controls=True)
    report = {
        "schema": "shared-observation-modeled-native-ledger/v1",
        "evidence_type": "EXECUTED_NATIVE_ACCOUNTING_WITH_MODELED_AMOUNTS",
        "source_commands_sha256": sha256(raw),
        "replay": replay,
        "actual_customer_collections_usd": 0,
        "actual_complete_research_cost_usd": None,
        "actual_complete_research_profit_usd": None,
        "money_boundary": "Native arithmetic checks modeled entries; it does not verify sales, bank receipts or costs.",
        "production_authority": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commands", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.commands, args.out)
    print(json.dumps({"output": str(args.out), "native_report": result["replay"]["report"]}, allow_nan=False))

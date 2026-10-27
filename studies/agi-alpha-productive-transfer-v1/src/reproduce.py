# SPDX-License-Identifier: Apache-2.0
"""Replay recorded prospective inputs; never count this as new capability evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalize(value):
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items() if key != "resources"}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", choices=("primary", "followup"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    is_followup = args.campaign == "followup"
    prefix = "followup-" if is_followup else ""
    freeze = json.loads((ROOT / f"protocol/{prefix}candidate-freeze.json").read_text())
    inputs = json.loads((ROOT / f"protocol/{prefix}input-freeze.json").read_text())
    for row in freeze["files"]:
        assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"], row["path"]
    args.out.mkdir(parents=True, exist_ok=False)
    checked = []
    for task in inputs["tasks"]:
        raw = ROOT / task["path"]
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == task["sha256"]
        for arm in ("A", "B", "C"):
            output = args.out / f"{task['id']}-{arm}"
            command = ["node", str(ROOT / ("src/workbench_v2.mjs" if is_followup else "src/workbench.mjs")),
                       str(raw), arm, str(output)]
            if arm != "C":
                suffix = "request" if arm == "A" else "response"
                group = "transcripts/followup" if is_followup else "transcripts"
                command.append(str(ROOT / f"{group}/{arm}/{task['id']}.{suffix}.json"))
            subprocess.run(command, check=True, capture_output=True, timeout=45)
            expected_dir = "followup" if is_followup else "confirmation"
            original = json.loads((ROOT / f"results/{expected_dir}/{task['id']}/{arm}/delivery/result.json").read_text())
            replay = json.loads((output / "delivery/result.json").read_text())
            assert normalize(original) == normalize(replay), f"Semantic replay differs: {task['id']}/{arm}"
            checked.append({"task": task["id"], "arm": arm, "semanticIdentity": True})
    receipt = {"schema": "agi-alpha-recorded-input-replay/v1", "campaign": args.campaign,
               "status": "PASS", "checks": checked, "independentCustomerJobs": 0,
               "scope": "Exact stored response replay, comparing all result content except process resources. Not fresh model generation or an efficacy rerun."}
    (args.out / "replay-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": "PASS", "replays": len(checked), "freshJobs": 0}))


if __name__ == "__main__":
    main()

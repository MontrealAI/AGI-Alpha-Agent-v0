# SPDX-License-Identifier: Apache-2.0
"""Prepare equal scientific inputs for fresh hosted recipients; no model calls."""

from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]


def inventory(root):
    return {
        str(p.relative_to(root)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--instrument-dir", required=True, type=Path)
    args = parser.parse_args()
    freeze = json.loads((HERE / "PROTOCOL_FREEZE.json").read_text())
    for relative, expected in freeze["files"].items():
        actual = hashlib.sha256((STUDY / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit("Frozen protocol changed: " + relative)
    for arm in ("U", "E", "E_plus"):
        root = args.out / ("S3_" + arm)
        if root.exists():
            raise SystemExit("Refusing to overwrite " + str(root))
        task = root / "tasks/qualification"
        shutil.copytree(HERE / "public_case", task)
        operator = "Complete the source-bound scientific qualification portfolio in tasks/qualification/BRIEF.md. Use the available conventional mathematical tools and inspect the supplied evidence carefully. Produce a tested executable submission, packet and concise report. All filesystem and Python interactions must use the logged runner. Do not inspect other arms or protected evaluation material.\n"
        if arm in ("E", "E_plus"):
            shutil.copy2(STUDY / "workflows/expert_v1.json", root / "EXPERT_WORKFLOW.json")
            operator += "Use the established versioned expert workflow in EXPERT_WORKFLOW.json.\n"
        if arm == "E_plus":
            shutil.copytree(
                args.instrument_dir, task / "capability", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
            operator += "You additionally receive the frozen generic instrument under tasks/qualification/capability. Inspect its scope and use it where applicable; preserve its source bytes. Receiving it is not authority or proof that it applies to the new mission.\n"
        (root / "OPERATOR.md").write_text(operator)
        state = {
            "arm": "S3_" + arm,
            "closed": False,
            "started_at": None,
            "operations": 0,
            "operations_limit": 48,
            "wall_seconds_limit": 1200,
            "test_executions": 0,
            "tool_elapsed_seconds": 0.0,
            "output_bytes": 0,
            "model": "same inherited hosted GPT-6 Astra Pro; API snapshot unobserved",
            "token_counts": None,
            "actual_cost_usd": None,
            "initial_inventory": inventory(root),
        }
        (root / "state.json").write_text(json.dumps(state, indent=2) + "\n")
        (root / "events.jsonl").write_text("")
        print(json.dumps({"arm": "S3_" + arm, "path": str(root), "initial_files": len(state["initial_inventory"])}))


if __name__ == "__main__":
    main()

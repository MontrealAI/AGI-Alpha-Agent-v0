# SPDX-License-Identifier: Apache-2.0
"""Evaluate one explicit hypothetical package using the frozen exact checker."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    frozen = json.loads((HERE / "results/FREEZE.json").read_text())
    if hashlib.sha256((HERE / "checker.py").read_bytes()).hexdigest() != frozen["source_sha256"]:
        raise ValueError("checker differs from recorded source freeze")
    spec = importlib.util.spec_from_file_location("frozen_arrangement", HERE / "checker.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads(args.input.read_text())
    result = module.evaluate(data["plan"], data["inputs"], data.get("worlds"), ledgers=True)
    result["input_sha256"] = hashlib.sha256(args.input.read_bytes()).hexdigest()
    result["evidence_label"] = (
        "Conditional user-supplied inputs; not observed contracts, cost, revenue or authorization."
    )
    if args.out.exists():
        raise ValueError("refusing to overwrite an earlier package evaluation")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "conditional_admissible": result["conditional_admissible"],
                "actual_business_qualification": result["actual_business_qualification"],
                "reasons": result["reasons"],
                "output": str(args.out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

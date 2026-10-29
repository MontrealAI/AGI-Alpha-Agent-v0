# SPDX-License-Identifier: Apache-2.0
"""Qualify the stdlib supplier CLI from a wheel, not a checkout or live system."""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys


def qualify(source: Path, output: Path) -> dict:
    source = source.resolve()
    output = output.resolve()
    if output.exists() or output.is_relative_to(source):
        raise ValueError("Use a new qualification directory outside the source checkout")
    if Path.cwd().resolve().is_relative_to(source):
        raise ValueError("Run from outside the source checkout")
    if sys.prefix == sys.base_prefix:
        raise ValueError("Use the fresh wheel installation environment")
    matched = {}
    for name in ("catalog_product", "catalog_identity", "delta_acceptance", "delta_delivery"):
        module = importlib.import_module("contrib.enterprise_campaign." + name)
        if not module.__file__:
            raise ValueError("Installed module source is missing")
        installed = Path(module.__file__).resolve()
        if not installed.is_relative_to(Path(sys.prefix).resolve()) or installed.is_relative_to(source):
            raise ValueError("Module does not originate in the selected installed environment")
        relative = "contrib/enterprise_campaign/" + name + ".py"
        expected = (source / relative).read_bytes()
        if installed.read_bytes() != expected:
            raise ValueError("Installed module differs from qualified source: " + relative)
        matched[relative] = hashlib.sha256(expected).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    before = b"sku,name,price,note\r\nA,Alpha,10.00,local-a\r\nB,Beta,20.00,local-b\r\n"
    (output / "before.csv").write_bytes(before)
    (output / "delta.csv").write_bytes(b"sku,price\nA,12.50\n")
    env = {**os.environ, "PYTHONPATH": "", "PYTHONNOUSERSITE": "1"}
    command = [
        sys.executable,
        "-I",
        "-m",
        "contrib.enterprise_campaign.delta_delivery",
        "--before",
        str(output / "before.csv"),
        "--delta",
        str(output / "delta.csv"),
        "--keys",
        "sku",
        "--write-fields",
        "price",
        "--decimal-fields",
        "price",
        "--output",
        str(output / "delivery"),
    ]
    result = subprocess.run(command, cwd=output, env=env, text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError("Installed CLI failed: " + result.stderr)
    delivery = output / "delivery"
    accepted = json.loads((delivery / "acceptance.json").read_text())
    usage = json.loads((delivery / "usage.json").read_text())
    if accepted["verdict"] != "PASS_IN_SCOPE":
        raise ValueError("Delivery was not accepted within scope")
    expected = b"sku,name,price,note\nA,Alpha,12.50,local-a\nB,Beta,20.00,local-b\n"
    if (delivery / "updated.csv").read_bytes() != expected:
        raise ValueError("Installed output differs from independent fixed expectation")
    if (delivery / "rollback.csv").read_bytes() != before or (output / "before.csv").read_bytes() != before:
        raise ValueError("Rollback or original preservation failed")
    if usage["model_calls"] != 0 or usage["network_actions"] != 0 or usage["commercial_success"] != "UNESTABLISHED":
        raise ValueError("Unexpected activity or commercial claim")
    repeated = subprocess.run(command, cwd=output, env=env, text=True, capture_output=True, timeout=30)
    if repeated.returncode != 2 or "Output must be a new directory" not in repeated.stderr:
        raise ValueError("Existing evidence was not refused")
    (output / "delta.csv").write_bytes(b"sku,price\nNEW,12.50\n")
    refused = subprocess.run(
        command[:-1] + [str(output / "refused")], cwd=output, env=env, text=True, capture_output=True, timeout=30
    )
    if refused.returncode != 2 or (output / "refused").exists():
        raise ValueError("Unknown supplier key was not refused without delivery")
    receipt = {
        "schema": "agialpha/installed-supplier-delta/v1",
        "status": "PASS_IN_SCOPE",
        "matched_installed_files": matched,
        "source_head": os.environ.get("QUALIFICATION_HEAD_SHA", "UNSPECIFIED"),
        "controls": [
            "fixed output",
            "exact rollback",
            "original unchanged",
            "existing output refused",
            "new key refused",
        ],
        "model_calls": 0,
        "network_actions": 0,
        "scope": "Four installed stdlib modules and local CLI only; not full agent dependencies, customer delivery or commercial qualification.",
    }
    (output / "qualification.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args.source_root, args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

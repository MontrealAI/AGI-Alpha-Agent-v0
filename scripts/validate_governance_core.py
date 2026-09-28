# SPDX-License-Identifier: Apache-2.0
"""Require exact Python/browser calculations and portable evidence bytes."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
from typing import Any

from alpha_factory_v1.demos.solving_agi_governance.workbench import artifacts, read_json, evaluate
from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def validate(output: Path) -> dict[str, Any]:
    original = ROOT / "alpha_factory_v1/demos/solving_agi_governance/scenarios.json"
    assert original.read_bytes() == (ROOT / "docs/assets/governance/scenarios.json").read_bytes()
    cases = read_json(original)
    for index in range(120):
        case = deepcopy(cases[0])
        case["id"] = f"parity-{index}"
        case["title"] = "Unicode parity: α 🌌 é"
        case["incentives"].update(
            discountBps=[0, 1, 4999, 5000, 8000, 9999][index % 6],
            detectionBps=[0, 1, 5000, 9999, 10000][index % 5],
            stake=index * 100,
        )
        case["risk"].update(
            perActionFemto=[0, 1, 1000, 10**6, 10**15][index % 5],
            actions=[1, 1000, 10**12][index % 3],
            budgetFemto=[0, 10**12, 10**15][index % 3],
        )
        case["validators"][index % 4]["votes"] = [0, -3, 3, 4, -1000, 1000][index % 6]
        case["upgrade"]["now"] = case["upgrade"]["queuedAt"] + case["upgrade"]["delaySeconds"] + index - 60
        if index % 7 == 0:
            case["validators"][1]["controller"] = "atlas"
        if index % 11 == 0:
            case["upgrade"]["paused"] = True
        cases.append(case)
    code = f"""
import {{readFileSync}} from 'node:fs';
import {{webcrypto}} from 'node:crypto';
import {{evaluate,parse,verify}} from {json.dumps((ROOT / 'docs/assets/governance/engine.mjs').as_uri())};
import {{artifacts}} from {json.dumps((ROOT / 'docs/assets/governance/engine.mjs').as_uri())};
globalThis.crypto ??= webcrypto;
const cases=JSON.parse(readFileSync(0,'utf8')), results=[];
for(let i=0;i<cases.length;i++){{
  const report=await evaluate(cases[i]);
  results.push({{report,files:i<5?await artifacts(report):null}});
}}
for(const bad of ['{{"x":1,"x":2}}','{{"x":NaN}}','{{"x":Infinity}}']){{
  let rejected=false;
  try{{parse(bad);}}catch{{rejected=true;}}
  if(!rejected)throw Error('Ambiguous JSON accepted');
}}
const forged=structuredClone(results[0].report);forged.result.approval='APPROVED';
let rejected=false;
try{{await verify(forged);}}catch{{rejected=true;}}
if(!rejected)throw Error('Forged approval accepted');
process.stdout.write(JSON.stringify(results));
"""
    run = subprocess.run(
        ["node", "--input-type=module", "-e", code],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    browser = json.loads(run.stdout)
    records = []
    for index, (case, item) in enumerate(zip(cases, browser, strict=True)):
        native = evaluate(case)
        if native != item["report"]:
            raise ValueError(f"Python/browser calculation mismatch: {case['id']}")
        if index < 5:
            native_files = {name: data.decode("utf-8") for name, data in artifacts(native).items()}
            if native_files != item["files"]:
                different = [name for name in native_files if native_files[name] != item["files"].get(name)]
                raise ValueError(f"Python/browser export mismatch: {case['id']}: {different}")
            jobs = native["result"]["jobs"]
            if jobs:
                assert verify_plan(compile_plan(jobs))["valid"] is True
        records.append({"id": case["id"], "sha256": native["sha256"], "status": native["result"]["status"]})
    report = {
        "schema": "agialpha.governance.core-acceptance.v1",
        "passed": True,
        "cases": records,
        "exact_calculation_cases": len(cases),
        "exact_export_bundles": 5,
        "job_specs_compile": True,
        "duplicate_and_nonfinite_json_rejected": True,
        "forged_approval_rejected": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "core.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/governance-core"))
    result = validate(parser.parse_args().output)
    print(
        f"Verified {result['exact_calculation_cases']} exact Python/browser decisions, "
        "five identical export bundles and Ascension jobs"
    )

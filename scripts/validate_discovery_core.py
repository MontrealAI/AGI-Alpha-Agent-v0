# SPDX-License-Identifier: Apache-2.0
"""Require exact Python/browser Insight calculations and portable evidence bytes."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import subprocess
from typing import Any

from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import artifacts, read_json, evaluate
from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def validate(output: Path) -> dict[str, Any]:
    original = ROOT / "alpha_factory_v1/demos/alpha_agi_insight_v0/scenarios.json"
    assert original.read_bytes() == (ROOT / "docs/assets/discovery/scenarios.json").read_bytes()
    cases = read_json(original)
    rng = random.Random(937)
    for index in range(120):
        case = deepcopy(cases[0])
        case["id"] = f"parity-{index}"
        case["title"] = "Unicode parity: α 🌌 é <img src=x>"
        case["note"] = "[untrusted](javascript:attack) **claim**"
        case["policy"].update(reviewMinutes=index, minScoreBps=index * 73, minCoverageBps=index * 71)
        cuts = sorted([0, 10000, *[rng.randrange(10001) for _ in range(3)]])
        case["weights"] = dict(zip(case["weights"], [b - a for a, b in zip(cuts, cuts[1:])]))
        for opportunity in case["opportunities"]:
            for signal in opportunity["signals"].values():
                signal.update(zip(("low", "base", "high"), sorted(rng.randrange(10001) for _ in range(3))))
                if rng.randrange(5) == 0:
                    signal["source"] = ""
        cases.append(case)
    module_uri = json.dumps((ROOT / "docs/assets/discovery/engine.mjs").as_uri())
    code = f"""
import {{readFileSync}} from 'node:fs';
import {{evaluate,parse,verify,artifacts,digest}} from {module_uri};
const cases=JSON.parse(readFileSync(0,'utf8')), results=[];
for(let i=0;i<cases.length;i++){{
  const report=await evaluate(cases[i]);
  const files=i<5?Object.fromEntries(Object.entries(await artifacts(report))
    .map(([name,data])=>[name,new TextDecoder().decode(data)])):null;
  results.push({{report,files}});
}}
for(const bad of ['{{"x":1,"x":2}}','{{"x":NaN}}','{{"x":Infinity}}','{{"x":1e999}}','"\\\\ud800"']){{
  let rejected=false;try{{parse(bad);}}catch{{rejected=true;}}
  if(!rejected)throw Error('Ambiguous JSON accepted: '+bad);
}}
const forged=structuredClone(results[0].report);forged.result.selectedIds=[];
const {{sha256,...body}}=forged;forged.sha256=await digest(body);
let rejected=false;try{{await verify(forged);}}catch{{rejected=true;}}
if(!rejected)throw Error('Rehashed forgery accepted');
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
            assert verify_plan(compile_plan(native["result"]["jobs"]))["valid"] is True
        records.append({"id": case["id"], "sha256": native["sha256"], "status": native["result"]["status"]})
    report = {
        "schema": "agialpha.discovery.core-acceptance.v1",
        "passed": True,
        "cases": records,
        "exact_calculation_cases": len(cases),
        "exact_export_bundles": 5,
        "job_specs_compile": True,
        "duplicate_nonfinite_unicode_rejected": True,
        "rehashed_forgery_rejected": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "core.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/discovery-core"))
    result = validate(parser.parse_args().output)
    print(f"Verified {result['exact_calculation_cases']} exact decisions, five identical bundles and Ascension jobs")

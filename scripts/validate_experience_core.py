# SPDX-License-Identifier: Apache-2.0
"""Require exact Python/JavaScript learning, evaluation and evidence-bundle parity."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import subprocess

from alpha_factory_v1.demos.era_of_experience.lab import artifacts, evaluate, read_json
from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]


def validate(output: Path) -> dict[str, object]:
    cases = read_json(ROOT / "alpha_factory_v1/demos/era_of_experience/scenarios.json")
    rng = random.Random(291607)
    for index in range(80):
        case = deepcopy(cases[index % 4])
        case["id"] = f"parity-{index}"
        case["title"] = "Unicode α 🌌 é <img src=x>"
        case["seed"] = rng.randrange(1, 4294967296)
        case["training"].update(
            steps=rng.randrange(12, 601),
            evaluationSteps=rng.randrange(30, 601),
            memoryWindow=rng.randrange(1, 201),
            explorationBps=rng.randrange(10001),
        )
        case["training"]["shiftAt"] = rng.randrange(case["training"]["steps"] + 1)
        for field, maximum in (("costWeight", 100), ("incidentPenalty", 10000), ("proxyWeight", 100)):
            case["reward"][field] = rng.randrange(maximum + 1)
        for context in case["contexts"]:
            for phase in ("initial", "shifted"):
                for model in context[phase]:
                    model.update(
                        successBps=rng.randrange(10001),
                        incidentBps=rng.randrange(10001),
                        cost=rng.randrange(1001),
                        proxy=rng.randrange(1001),
                    )
        cases.append(case)
    module = json.dumps((ROOT / "docs/assets/experience/engine.mjs").as_uri())
    code = f"""
import {{readFileSync}} from 'node:fs';
import {{evaluate,artifacts,verify,parse,digest}} from {module};
const cases=JSON.parse(readFileSync(0,'utf8')),results=[];
for(let i=0;i<cases.length;i++){{
 const report=await evaluate(cases[i]);
 const files=i<4?Object.fromEntries(Object.entries(await artifacts(report))
   .map(([name,data])=>[name,new TextDecoder().decode(data)])):null;
 results.push({{report,files}});
}}
for(const bad of ['{{"x":1,"x":2}}','{{"x":1e999}}','"\\\\ud800"']){{
 let rejected=false;try{{parse(bad);}}catch{{rejected=true;}}if(!rejected)throw Error('Ambiguous JSON accepted');
}}
const forged=structuredClone(results[0].report);forged.result.training=[];
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
    results = json.loads(run.stdout)
    records = []
    for index, (case, result) in enumerate(zip(cases, results, strict=True)):
        native = evaluate(case)
        if native != result["report"]:
            raise ValueError(f"Learning or evaluation mismatch: {case['id']}")
        if index < 4:
            if {name: data.decode() for name, data in artifacts(native).items()} != result["files"]:
                raise ValueError(f"Evidence bundle mismatch: {case['id']}")
            assert verify_plan(compile_plan(native["result"]["jobs"]))["valid"]
        records.append({"id": case["id"], "sha256": native["sha256"], "status": native["result"]["status"]})
    report: dict[str, object] = {
        "schema": "agialpha.experience.core-acceptance.v1",
        "passed": True,
        "cases": records,
        "exact_learning_cases": len(cases),
        "exact_export_bundles": 4,
        "jobs_compile": True,
        "rehashed_forgery_rejected": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "core.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("evidence/experience-core"))
    result = validate(parser.parse_args().output)
    print(f"Verified {result['exact_learning_cases']} exact learning runs, four evidence bundles and review jobs")

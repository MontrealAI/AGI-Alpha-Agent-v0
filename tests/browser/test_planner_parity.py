# SPDX-License-Identifier: Apache-2.0
"""Compare browser solver with the independent Python solver on seeded scenarios."""
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
engine = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "alpha_factory_v1/demos/alpha_super_planner_v1/planner.py"
spec = importlib.util.spec_from_file_location("bounded_planner", engine)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
rng = random.Random(72613)
cases = []
for n in range(120):
    tasks = []
    for i in range(rng.randint(1, 10)):
        tasks.append(
            {
                "id": f"t{i}",
                "label": f"Task {i}",
                "cost": rng.randint(0, 10),
                "effort": rng.randint(0, 8),
                "value": rng.randint(0, 12),
                "risk": rng.randint(0, 100),
                "requires": [f"t{j}" for j in range(i) if rng.random() < 0.15],
            }
        )
    cases.append(
        {
            "schema": "agialpha.bounded-plan.v1",
            "goal": f"Parity scenario {n}",
            "budget": rng.randint(0, 30),
            "effort_capacity": rng.randint(0, 25),
            "max_risk": rng.randint(0, 100),
            "tasks": tasks,
        }
    )
script = (
    "import {solve} from "
    + json.dumps((ROOT / "docs/alpha_super_planner_v1/assets/engine.mjs").as_uri())
    + ";let text='';for await(const chunk of process.stdin)text+=chunk;"
    "console.log(JSON.stringify(JSON.parse(text).map(solve)));"
)
actual = json.loads(
    subprocess.check_output(["node", "--input-type=module", "-e", script], input=json.dumps(cases).encode())
)
expected = [module.solve(case) for case in cases]
assert actual == expected
print(f"PASS: {len(cases)} seeded Python/JavaScript full-result parity cases")

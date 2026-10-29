# SPDX-License-Identifier: Apache-2.0
"""Fresh source-bound use of the capability constructed after the funding decision."""

import hashlib
import json
from pathlib import Path
import random
import secrets
import sys
import time

from alpha_factory_v1.core.runtime.claim_probe import contracts, joint, joint_check


def run(output):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[2]
    files = [
        source / "alpha_factory_v1/core/runtime/claim_probe/joint.py",
        source / "alpha_factory_v1/core/runtime/claim_probe/joint_check.py",
        Path(__file__),
        Path(__file__).with_name("test_joint.py"),
    ]
    frozen = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (out / "freeze.json").write_text(
        json.dumps(
            {
                "files": frozen,
                "tasks": 24,
                "dimensions": [2, 3, 4, 5],
                "scope": "New mathematical input class, no physical or discovery-superiority claim",
                "controls": "Exact direct corner enumeration, same mathematical theorem",
            },
            indent=2,
        )
        + "\n"
    )
    seed = secrets.randbits(48)
    (out / "freshness.json").write_text(
        json.dumps(
            {
                "seed": seed,
                "seedAfterSourceFreeze": True,
                "freezeSha256": hashlib.sha256((out / "freeze.json").read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    rng = random.Random(seed)
    rows = []
    cpu = time.process_time()
    for i in range(24):
        d = 2 + i % 4
        c = [rng.randint(-3, 3) for _ in range(2**d)]
        if i % 2 == 0:
            c[0] = sum(abs(x) for x in c[1:]) + 1
        else:
            c[0] = -1
        task = {
            "schema": "agialpha/joint-affine-claim/v1",
            "id": f"fresh-joint-{i}",
            "variables": [f"x{j}" for j in range(d)],
            "coefficients": list(map(str, c)),
            "domain": [["0", "1"] for _ in range(d)],
            "sources": ["https://www.nist.gov/mml/mmsd/data-and-ai-driven-materials-science-group/autonomous-methods"],
            "claim": "nonnegative-throughout-box",
            "scope": "declared-mathematical-model-only",
        }
        rejected = False
        try:
            contracts.validate(task)
        except ValueError:
            rejected = True
        result = joint.construct_and_check(task)
        conventional, points = joint_check.reference(task)
        expected = "PROVED" if min(conventional) >= 0 else "REFUTED"
        rows.append(
            {
                "task": task,
                "result": result,
                "predecessorSchemaRefused": rejected,
                "ordinaryControlStatus": expected,
                "ordinaryControlMinimum": str(min(conventional)),
                "sameDecision": result["artifact"]["status"] == expected,
            }
        )
    elapsed = time.process_time() - cpu
    with (out / "tasks.jsonl").open("x") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    summary = {
        "tasks": len(rows),
        "accepted": sum(x["result"]["verification"]["accepted"] for x in rows),
        "predecessorRefusals": sum(x["predecessorSchemaRefused"] for x in rows),
        "conventionalTies": sum(x["sameDecision"] for x in rows),
        "CPUSeconds": elapsed,
        "sourceFrozen": all(
            hashlib.sha256(p.read_bytes()).hexdigest() == frozen[str(p.relative_to(source))] for p in files
        ),
        "scope": "Actual fresh mathematical use of new software; ordinary available method ties. Economic benefit remains conditional on modeled need; no independently measured retention advantage.",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run(sys.argv[1])

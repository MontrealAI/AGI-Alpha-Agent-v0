#!/usr/bin/env python3
"""Targeted, independently executable tests of audited information boundaries."""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim"))
import economy

def run():
    config, register = economy.load_inputs(ROOT / "sim/config.json")
    config["_stages"] = register["stages"]
    table = economy.cost_table(register)
    belief = economy.Belief(np.ones(9) / 9, 2, .5)
    graph = economy.make_simulated_record("R", 0, 1, 18, [0, 1, 2, 3, 4], True)
    asset = economy.Asset("R", 1, True, .95, .8, np.ones(12, dtype=bool), graph)
    before = economy.price_plan(config, config["scenarios"]["central"], table,
                                belief, {"R": asset}, 3, "optimized_optional")
    asset.good = False
    asset.transfer = np.zeros(12, dtype=bool)
    after = economy.price_plan(config, config["scenarios"]["central"], table,
                               belief, {"R": asset}, 3, "optimized_optional")
    assert before == after
    dimensions = [
        {"usd": 1, "tokens": 2, "minutes": 3, "container_minutes": 4},
        {"usd": 5, "tokens": 6, "minutes": 7, "container_minutes": 8},
    ]
    assert economy.resource_sum(iter(dimensions)) == {
        "usd": 6, "tokens": 8, "minutes": 10, "container_minutes": 12
    }
    return {
        "status": "PASS",
        "basis": "Independent controller-information and iterable-resource checks",
        "source_sha256": hashlib.sha256((ROOT / "sim/economy.py").read_bytes()).hexdigest(),
        "checks": [
            "Changing latent asset goodness and all future recipient-transfer outcomes leaves the same observable-state price plan exactly unchanged.",
            "A one-use generator contributes every resource dimension, preventing the earlier development-pilot accounting defect."
        ],
        "scope": "Not a full policy optimality proof or empirical calibration."
    }

if __name__ == "__main__":
    report = run()
    (ROOT / "qa/controller_information_audit.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))

# SPDX-License-Identifier: Apache-2.0
"""Independent arithmetic audit of this frozen report, not a production calculator."""
from fractions import Fraction as F
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
scope = json.loads((ROOT / "economic-scope.json").read_text())
report = json.loads((ROOT / "modeled-cost-results.json").read_text())
inputs = json.loads((ROOT / "modeled-cost-inputs.json").read_text())
assert inputs["schema"] == "alpha-automated-costs/v1" and report["schema"] == "alpha-automated-cost-summary/v1"
checks = 0
for case, result, declared in zip(scope["simulationParameters"], report["scenarios"], inputs["scenarios"], strict=True):
    requests = F(case["capacity"] * case["utilization"], 10000)
    accepted = requests * F(case["acceptance"], 10000)
    attempts = F(case["attempts"], 1000000)
    assert 1 <= attempts <= 2
    rate = -(-case["host"] // (30 * 24 * 3600))
    active = requests * attempts * case["seconds"] * rate
    residual = F(case["exceptions"], 1000000) * case["exceptionMinutes"] * F(74420000, 60)
    marginal = (attempts * case["seconds"] * rate + residual) * requests / accepted
    # Full monthly hardware appears ONCE, regardless of active/standby allocation.
    recurring = (case["host"] + requests * residual + case["upkeep"] + case["business"]) / accepted
    loaded = recurring + F(case["development"] + case["setup"], case["months"]) / accepted
    for name, expected in [("marginal", marginal), ("recurring", recurring), ("fullyLoaded", loaded)]:
        rounded = -(-expected.numerator // expected.denominator)
        assert result["costs"][name + "MicrosPerAccepted"] == rounded
        assert result["comparison"][name]["outcome"] == "unknown"
        assert abs(result["comparison"][name]["breakEvenHumanMinutes"] - float(expected * 60 / 74420000)) < 1e-9
        checks += 3
    monthly = declared["monthly"][0]["amountMicros"]["value"]
    assert active + monthly == case["host"]
    assert result["volume"]["acceptedPerMonth"] == accepted
    assert declared["humanBaseline"]["minutesPerAccepted"]["value"] is None
    assert all(row["unitsPerOccurrencePpm"]["basis"] == "estimated" for row in declared["operations"])
    checks += 4
assert all(
    scope[k] is None
    for k in ("actualFullCurrencyCosts", "customerPrice", "customerEffortMinutes", "collections", "availableSurplus")
)
print(
    json.dumps(
        {
            "schema": "alpha-frozen-cost-report-audit/v1",
            "passed": True,
            "checks": checks + 5,
            "productionImplementation": "examples/successor-alpha/automated-costs.mjs",
            "interpretation": "All monetary results are simulated assumptions; matched human duration and customer savings remain unknown.",
        }
    )
)

"""Exact finite construction for an archival-measurement candidate.

This is synthetic, not a benchmark on historical scans. All quantities are
integer tenths of a measurement unit. A certificate is conditional on the
admissible-world model, including its shared-calibration assumption.
"""
from fractions import Fraction
from itertools import product
import json
from pathlib import Path

BASE = (200, 201, 202, 203, 210, 211, 212, 213)
THRESHOLD = Fraction(35, 100)
ERRORS = [(None, 0)] + [(i, e) for i in range(8) for e in (-1, 1)]


def examine(shared_calibration):
    calibration_pairs = [(c, c) for c in (-4, 0, 4)] if shared_calibration else list(product((-4, 0, 4), repeat=2))
    low = high = None
    low_world = high_world = None
    count = 0
    for alternatives in product((0, 6), repeat=8):
        for c_early, c_late in calibration_pairs:
            for error_index, error in ERRORS:
                readings = [BASE[i] + alternatives[i] + (c_early if i < 4 else c_late) + (error if error_index == i else 0) for i in range(8)]
                change = Fraction(sum(readings[4:]) - sum(readings[:4]), 40)
                world = {"glyph_offsets_tenths": alternatives, "calibration_tenths": [c_early, c_late], "source_error": [error_index, error], "true_values_tenths": readings}
                count += 1
                if low is None or change < low:
                    low, low_world = change, world
                if high is None or change > high:
                    high, high_world = change, world
    return {"worlds_checked": count, "lower": str(low), "upper": str(high), "claim": "late mean minus early mean > 0.35 units", "claim_certified": low > THRESHOLD, "counterexample_exists": low <= THRESHOLD, "lower_witness": low_world, "upper_witness": high_world}


result = {
    "kind": "synthetic exact finite construction",
    "not_demonstrated": ["accurate admissible-world extraction from real scans", "novelty", "paid demand", "labor savings"],
    "obligations": ["Each glyph alternative is 0 or +0.6 units from the printed base.", "Calibration is one of -0.4, 0, +0.4 units.", "At most one source entry has an extra -0.1 or +0.1 unit error.", "The shared-calibration result assumes both epochs used the same calibration; the negative control removes that assumption.", "All glyph alternatives remain unresolved."],
    "shared_calibration": examine(True),
    "independent_calibration_negative_control": examine(False),
}
assert result["shared_calibration"]["lower"] == "3/8"
assert result["shared_calibration"]["upper"] == "13/8"
assert result["shared_calibration"]["claim_certified"]
assert result["independent_calibration_negative_control"]["lower"] == "-17/40"
assert result["independent_calibration_negative_control"]["upper"] == "97/40"
assert not result["independent_calibration_negative_control"]["claim_certified"]
out = Path(__file__).with_name("expert_discovery_exact_result.json")
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: {a: b for a, b in v.items() if "witness" not in a} if isinstance(v, dict) else v for k, v in result.items()}, indent=2))

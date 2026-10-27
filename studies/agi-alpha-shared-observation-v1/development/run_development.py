# SPDX-License-Identifier: Apache-2.0
import copy
import hashlib
import importlib.util
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("compiler", ROOT / "capability/compiler.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
mission = {
    "schema": "shared-observation-mission/v1", "mission_id": "origin-three-operators",
    "evidence_type": "synthetic", "calibration_scope": "shared-secondary-risk-v1",
    "states": ["offset-far", "offset-near"], "prior": [0.8, 0.2],
    "observation": {"id": "shared-offset-observation", "usable": True, "rights_cleared": True,
                    "calibration_scope": "shared-secondary-risk-v1", "outcomes": [
                        {"id": "clearer-separation", "likelihood": [0.90, 0.05], "arrival_hours": 2},
                        {"id": "closer-approach", "likelihood": [0.06, 0.85], "arrival_hours": 2},
                        {"id": "no-result", "likelihood": [0.04, 0.10], "arrival_hours": None}]},
    "operators": [{"id": f"operator-{i+1}", "risk_limit": 0.0001,
                   "decision_deadline_hours": 4, "fallback_action": "maneuver", "actions": [
                       {"id": "coast", "risk_by_state": [0.000001, dangerous], "cost_usd": 0, "latest_start_hours": 8},
                       {"id": "maneuver", "risk_by_state": [0.0000001, 0.000001], "cost_usd": cost,
                        "latest_start_hours": 4}]}
                  for i, (dangerous, cost) in enumerate([(0.0008, 500), (0.001, 650), (0.0015, 800)])],
}
cases = [("origin", mission, True)]
for label in ["late", "wrong-scope", "rights-missing", "no-value", "bad-fallback", "unreachable", "withdrawal"]:
    m = copy.deepcopy(mission)
    m["mission_id"] = "development-" + label
    expected = True
    if label == "late":
        for o in m["observation"]["outcomes"]:
            o["arrival_hours"] = 10
    elif label == "wrong-scope":
        m["observation"]["calibration_scope"] = "different-measurement-law"
        expected = False
    elif label == "rights-missing":
        m["observation"]["rights_cleared"] = False
        expected = False
    elif label == "no-value":
        for o in m["observation"]["outcomes"]:
            o["likelihood"] = [0.5, 0.5] if o["id"] != "no-result" else [0.0, 0.0]
    elif label == "bad-fallback":
        for op in m["operators"]:
            op["fallback_action"] = "coast"
        expected = False
    elif label == "unreachable":
        m["observation"]["outcomes"].append({"id": "never", "likelihood": [0, 0], "arrival_hours": 1})
    elif label == "withdrawal":
        m["operators"].pop()
    cases.append((label, m, expected))
rows = []
for label, m, expected in cases:
    raw = (json.dumps(m, indent=2) + "\n").encode()
    path = ROOT / "development" / (label + ".json")
    path.write_bytes(raw)
    started = time.perf_counter()
    result = module.compile_mission(m)
    elapsed = time.perf_counter() - started
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    (ROOT / "development" / (label + ".result.json")).write_text(json.dumps(result, indent=2) + "\n")
    rows.append({"id": label, "accepted": result["observation_accepted"], "expected_acceptance": expected,
                 "matched": result["observation_accepted"] == expected, "seconds": elapsed,
                 "baseline": result["total_baseline_cost"], "contingent": result["total_contingent_cost"],
                 "information_value": result["total_value_of_information"]})
(ROOT / "data/origin.json").write_bytes((ROOT / "development/origin.json").read_bytes())
(ROOT / "results/origin.json").write_bytes((ROOT / "development/origin.result.json").read_bytes())
(ROOT / "development/development_results.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps(rows, indent=2))
if not all(row["matched"] for row in rows):
    raise SystemExit(1)

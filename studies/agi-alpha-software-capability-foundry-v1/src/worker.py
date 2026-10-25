# SPDX-License-Identifier: Apache-2.0
"""One finite disposable research operation. No network and no scheduler."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from constructor import ROOT, construct_child, identity, load, retain_reader
from drift_core import compare
from measurement import measured
PARTIAL_COSTS = []
PARTIAL_RECORDS = []

def run(request: dict) -> dict:
    global PARTIAL_COSTS, PARTIAL_RECORDS
    arm, phase = request["arm"], request["phase"]
    work = Path(request["work"])
    work.mkdir(parents=True, exist_ok=True)
    repo, commit, paths = Path(request["repo"]), request["commit"], request["paths"]
    config = json.loads((ROOT / "protocol/selection.json").read_text())
    selected = ROOT / config["selected_source"]
    specialist = ROOT / "review/specialist.py"
    equivalent = ROOT / config["equivalent_source"]
    asset_dir = work / "asset"
    asset_arms = {"flywheel", "conventional", "equivalent", "reconstruction"}
    costs, records = [], []
    PARTIAL_COSTS, PARTIAL_RECORDS = costs, records
    if phase == "read":
        source = specialist if arm in {"specialist", "no_asset"} else selected
        if arm == "equivalent":
            source = equivalent
        if arm in asset_arms:
            source_for_copy = ROOT / config["template_source"] if arm == "reconstruction" else source
            record, cost = measured(lambda: retain_reader(source_for_copy, asset_dir,
                {"basis": "development A acceptance", "source_sha256": identity(source_for_copy),
                 "development_record": config["qualification_sha256"]}))
            costs.append({"account": "improvement", "stage": "reader_materialization", **cost})
            source = asset_dir / "reader.py"
        module, cost = measured(lambda: load(source))
        costs.append({"account": "service", "stage": "load_reader", **cost})
        for repeat in range(request["repeats"]):
            value, cost = measured(lambda: module.read(repo, commit, paths))
            result = {p: {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()} for p,b in sorted(value.items())}
            costs.append({"account": "service", "stage": "read", "repeat": repeat,
                          "condition": "fresh_process" if repeat == 0 else "warm_process", **cost})
            records.append({"repeat": repeat, "files": result})
        return {"arm": arm, "phase": phase, "source_sha256": identity(source), "records": records, "costs": costs}
    if phase != "child":
        raise ValueError("Unknown finite operation")
    if arm in asset_arms:
        acceptance = request["acceptance"]
        record, cost = measured(lambda: construct_child(asset_dir, acceptance))
        costs.append({"account": "improvement", "stage": "child_construction", **cost})
        module, cost = measured(lambda: load(asset_dir / "drift.py"))
        diagnose = module.diagnose
    else:
        source = specialist if arm in {"specialist", "no_asset"} else selected
        module, cost = measured(lambda: load(source))
        if arm in {"specialist", "no_asset"}:
            diagnose = module.direct_diagnose
        else:
            diagnose = lambda r,c,p,a: compare(module.read(r,c,p), a)
    costs.append({"account": "service", "stage": "load_diagnostic", **cost})
    for repeat in range(request["repeats"]):
        result, cost = measured(lambda: diagnose(repo, commit, paths, Path(request["archive"])))
        costs.append({"account": "service", "stage": "diagnose", "repeat": repeat,
                      "condition": "fresh_process" if repeat == 0 else "warm_process", **cost})
        records.append({"repeat": repeat, "result": result})
    return {"arm": arm, "phase": phase, "records": records, "costs": costs}

if __name__ == "__main__":
    request = json.loads(sys.stdin.read())
    try:
        response = run(request)
        response["status"] = "completed"
    except Exception as error:
        response = {"status": "failed", "error": type(error).__name__, "message": str(error),
                    "arm": request.get("arm"), "phase": request.get("phase"),
                    "costs": PARTIAL_COSTS, "records": PARTIAL_RECORDS}
    print(json.dumps(response, ensure_ascii=False, sort_keys=True))

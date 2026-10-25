"""Check the saved corrective qualifier with the reviewer implementation."""

import hashlib, json
from pathlib import Path
import independent_evidence_audit as audit

ROOT = Path(__file__).resolve().parents[1]


def read(p):
    return json.loads(p.read_text())


target = ROOT / "outputs/correction-confirmation"
freeze = read(ROOT / "protocol/experiment-v11-FREEZE.json")
freeze_hash = hashlib.sha256((ROOT / "protocol/experiment-v11-FREEZE.json").read_bytes()).hexdigest()
for entry in freeze["entries"]:
    b = (ROOT / entry["path"]).read_bytes()
    audit.require(
        len(b) == entry["bytes"] and hashlib.sha256(b).hexdigest() == entry["sha256"],
        "corrective frozen file " + entry["path"],
    )
base = read(target / "base-input.json")
rows = []
initial = {}
fresh = {}
for arm in ["full_rebuild", "flywheel", "conventional_cache"]:
    initial[arm] = read(target / (arm + "-initial.json"))["result"]
    r = initial[arm]
    result = audit.inspect_result(base, r, None, arm, arm + " initial", path_keys=True)
    audit.require(r["pack"]["frozen"]["sourceHash"] == freeze_hash, arm + " initial freeze binding")
    rows.append({"case": arm + " initial", "pass": result["accepted_by_review"]})
    for file in sorted(target.glob(arm + "-*-input.json")):
        name = file.name.removesuffix("-input.json")
        p = read(file)
        r = read(target / (name + "-execution.json"))["result"]
        prev = initial[arm]["state"]
        result = audit.inspect_result(p, r, prev, arm, name, path_keys=True)
        audit.require(r["pack"]["frozen"]["sourceHash"] == freeze_hash, name + " freeze binding")
        built = read(target / (name + "-construction.json"))["result"]
        audit.require(built["parent"] == result["parent"], name + " actual construction parent")
        child = built["child"]
        audit.require(
            child["parent_digest"] == audit.digest("evidence-index", built["parent"])
            and child["origin_parent"] == built["parent"],
            name + " retained origin",
        )
        audit.require(
            child["digest"] == audit.digest("dependency-repair", audit.without(child, "digest")),
            name + " child identity",
        )
        if arm == "flywheel":
            audit.require(
                r["state"]["child_registry"]
                == {"child_digest": child["digest"], "origin_digest": child["parent_digest"]},
                name + " admitted first-use registry",
            )
            audit.require(r["impact"]["child_digest"] == child["digest"], name + " actual child use")
        receipt = read(target / (name + "-acceptance.json"))
        audit.require(receipt["accepted"] == result["accepted_by_review"], name + " independent receipt agreement")
        rows.append({"case": name, "pass": result["accepted_by_review"]})
        if arm == "flywheel" and name.endswith("fresh-content"):
            fresh = {"result": r, "child": child}
continued = read(target / "child-second-use.json")
r = continued["execution"]["result"]
result = audit.inspect_result(
    continued["input"], r, fresh["result"]["state"], "flywheel", "child second use", path_keys=True
)
audit.require(
    r["state"]["child_registry"] == fresh["result"]["state"]["child_registry"], "second use preserves origin registry"
)
audit.require(r["impact"]["child_digest"] == fresh["child"]["digest"], "second use actual original child")
audit.require(r["pack"]["frozen"]["sourceHash"] == freeze_hash, "second use freeze binding")
rows.append({"case": "child-second-use", "pass": result["accepted_by_review"]})
for name, error in [
    ("cross-project-parent", "PARENT_PROJECT_BINDING"),
    ("unrelated-child-origin", "CHILD_ORIGIN_BINDING"),
    ("tampered-child", "CHILD_BINDING"),
]:
    r = read(target / (name + ".json"))
    ok = r["ok"] is False and r["error"] == error
    audit.require(ok, name + " refusal")
    rows.append({"case": name, "pass": ok})
summary = read(target / "summary.json")
audit.require(
    summary["development"] is False and summary["seed"] == 202610252919, "separate fresh corrective designation"
)
audit.require(
    summary["case_count"] == len(rows) == 28 and summary["accepted"] == sum(x["pass"] for x in rows),
    "corrective case totals",
)
report = {
    "status": "PASS" if not audit.failures else "FAIL",
    "checks": audit.checks,
    "failures": audit.failures,
    "case_count": len(rows),
    "pass_count": sum(x["pass"] for x in rows),
    "recorded_successful_outputs": 25,
    "recorded_expected_refusals": 3,
    "frozen_corrective_files_verified": len(freeze["entries"]),
    "rows": rows,
    "independence": "Reviewer-owned implementation imports no producer/oracle/solver; common session/model/source custody. This checks saved results and does not replay the qualifier or convert development probes into held-out cases.",
    "scope": "Corrective finite engineering qualification, separate from unchanged primary timing results.",
}
(ROOT / "review/INDEPENDENT_CORRECTION_AUDIT.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
raise SystemExit(0 if not audit.failures else 1)

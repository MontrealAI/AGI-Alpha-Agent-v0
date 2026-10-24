# SPDX-License-Identifier: Apache-2.0
"""Read-only analytic review added after freeze, before reviewing confirmation.

This checker imports no experimental compiler, optimizer, evaluator, or analysis.
It exploits only the declared four-tick geometry and positive job weights. It is
not a replacement for replaying observations and authenticating the ledgers.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time


METHODS = {"idea", "greedy", "disclosed", "verified", "clone", "expert", "adaptive-expert"}
CONDITIONS = {
    "ordinary", "capacity-doubled", "tight-validity", "measurement-drift",
    "demand-drift", "reliability-failure", "cheap-calibration", "expensive-evidence",
}


def nominal_bound(mission, method):
    """Return (optimal modeled utility, minimum calibrations, scalar objective)."""
    if mission["horizon"] != 4 or len(mission["jobs"]) != 4:
        raise ValueError("Outside declared geometry")
    weights = sorted((j["utility"] for j in mission["jobs"]), reverse=True)
    if any(not isinstance(w, int) or w <= 0 for w in weights):
        raise ValueError("Closed-form bound assumes positive integer weights")
    capacity, duration = mission["capacity"], mission["calibrationDuration"]
    ttl = {job["ttl"] for job in mission["jobs"]}
    if (capacity, duration, tuple(ttl)) not in {(1, 1, (3,)), (1, 1, (1,)), (2, 1, (3,)), (1, 0, (3,))}:
        raise ValueError("Outside predeclared single-factor stress shapes")
    if method == "idea":
        jobs, calibrations = (3, 3) if duration == 0 else (min(4, 2 * capacity), 2)
    elif ttl == {1}:
        jobs, calibrations = 2, 2
    else:
        jobs, calibrations = min(4, 3 * capacity), 1
    prior = mission.get("pastQc")
    if method == "adaptive-expert" and prior is not None:
        bias = prior["relativeBias"]
        if len(bias) != 4:
            raise ValueError("Invalid diagnostic profile")
        if max(bias) - min(bias) > 1e-9:
            if not (capacity == 1 and duration == 1 and ttl == {3}
                    and abs(bias[0] - bias[1]) < 1e-9
                    and abs(bias[2] - bias[3]) < 1e-9
                    and abs(bias[2] - bias[0]) > 0.25):
                raise ValueError("Outside predeclared repeatable drift profile")
            # Samples at 1 and 3, calibrations at 0 and 2 attain this bound.
            # A third sample would either occupy a calibration tick or use a
            # calibration across the known jump, so cannot be predicted useful.
            jobs, calibrations = 2, 2
    utility = sum(weights[:jobs])
    return utility, calibrations, 100 * (sum(weights) - utility) + calibrations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    timer = time.perf_counter()
    source = args.input / "missions.jsonl.gz"
    if not source.exists():
        source = args.input / "missions.jsonl"
    report = {
        "schema": "nova-independent-analytic-bound-audit/v1",
        "reviewScope": "Post-freeze analytic verification, no source tuning; not external institutional peer review",
        "startedAt": started,
        "auditorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input": str(source),
        "inputSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "rows": 0, "worlds": 0, "nominalObjectivesChecked": 0,
        "comparisonsToVerified": {m: {"worlds": 0, "objectiveMismatches": 0, "planMismatches": 0,
                                      "utilityMismatches": 0, "completedCountMismatches": 0,
                                      "fullOutcomeMismatches": 0, "firstExamples": []}
                                  for m in ["clone", "expert", "disclosed", "greedy"]},
        "errors": [],
        "analyticalReasoning": [
            "All offered utility weights are positive: among k attainable job slots choose the k largest weights.",
            "One calibration at tick 0 opens three ordinary samples; capacity two admits all four jobs with one calibration.",
            "Unit TTL or immediate-prior calibration permits sample ticks 1 and 3 with calibrations 0 and 2.",
            "Zero-duration immediate-prior calibration permits samples 1,2,3 using calibrations 0,1,2.",
            "After a known repeatable tick-2 bias jump, useful samples 1 and 3 require calibrations 0 and 2.",
            "Positive weights and objective scale 100 make admitted utility primary and calibration count secondary.",
        ],
        "limits": [
            "Greedy is compared but not asserted to attain the analytic optimum under all worlds.",
            "Nominal optimality does not establish true physical usefulness; replay audit checks the synthetic observations separately.",
            "Resource and timing outcomes are not inferred from equality of objective or useful output.",
        ],
    }
    identities = set()

    def audit_group(group):
        if not group:
            return
        report["worlds"] += 1
        first = group[0]
        identity = (first["scenario"], first["seed"], first["epoch"])
        label = list(identity)
        if identity in identities:
            report["errors"].append({"code": "duplicate-world", "identity": label})
        identities.add(identity)
        by_method = {row["method"]: row for row in group}
        if len(group) != 7 or set(by_method) != METHODS:
            report["errors"].append({"code": "method-set", "identity": label})
            return
        for method, row in by_method.items():
            if row["status"] != "complete":
                report["errors"].append({"code": "incomplete-record", "identity": label, "method": method})
                continue
            if method != "greedy":
                try:
                    utility, calibrations, objective = nominal_bound(row["world"]["mission"], method)
                    report["nominalObjectivesChecked"] += 1
                    if row["result"]["objective"] != objective:
                        report["errors"].append({"code": "nominal-objective", "identity": label,
                                                 "method": method, "reported": row["result"]["objective"],
                                                 "expected": objective, "expectedModeledUtility": utility,
                                                 "expectedCalibrations": calibrations})
                except Exception as exc:
                    report["errors"].append({"code": "bound-not-applicable", "identity": label,
                                             "method": method, "reason": str(exc)})
        verified = by_method["verified"]
        if verified["status"] != "complete":
            return
        for method, comparison in report["comparisonsToVerified"].items():
            row = by_method[method]
            if row["status"] != "complete":
                continue
            comparison["worlds"] += 1
            checks = {
                "objectiveMismatches": row["result"]["objective"] != verified["result"]["objective"],
                "planMismatches": row["result"]["plan"] != verified["result"]["plan"],
                "utilityMismatches": row["outcome"]["utility"] != verified["outcome"]["utility"],
                "completedCountMismatches": row["outcome"]["completedJobs"] != verified["outcome"]["completedJobs"],
                "fullOutcomeMismatches": row["outcome"] != verified["outcome"],
            }
            for key, differs in checks.items():
                comparison[key] += int(differs)
            if any(checks.values()) and len(comparison["firstExamples"]) < 3:
                comparison["firstExamples"].append({"identity": label, "differences": checks,
                                                    "utility": row["outcome"]["utility"],
                                                    "verifiedUtility": verified["outcome"]["utility"]})

    group = []
    opener = gzip.open if source.suffix == ".gz" else open
    with opener(source, "rt") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            report["rows"] += 1
            identity = (row["scenario"], row["seed"], row["epoch"])
            if group and identity != (group[0]["scenario"], group[0]["seed"], group[0]["epoch"]):
                audit_group(group)
                group = []
            group.append(row)
    audit_group(group)
    expected = {(condition, seed, epoch) for condition in CONDITIONS
                for seed in range(101, 133) for epoch in range(12)}
    if identities != expected:
        report["errors"].append({"code": "confirmation-design-identities",
                                 "missing": [list(x) for x in sorted(expected - identities)],
                                 "unexpected": [list(x) for x in sorted(identities - expected)]})
    report["finishedAt"] = datetime.now(timezone.utc).isoformat()
    report["wallSeconds"] = time.perf_counter() - timer
    report["errorCount"] = len(report["errors"])
    report["passed"] = not report["errors"]
    text = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

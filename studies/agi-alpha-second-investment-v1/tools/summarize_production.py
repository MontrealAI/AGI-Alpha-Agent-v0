#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Summarize the one frozen cohort without rerunning or extending it."""
import csv
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    campaign_path = ROOT / "results/confirmation-01/campaign.json"
    campaign = json.loads(campaign_path.read_text())
    assert campaign["phase"] == "fresh-confirmation" and not campaign["partial"]
    assert len(campaign["rows"]) == 18
    freeze_path = ROOT / "protocol/production-freeze.json"
    freeze = json.loads(freeze_path.read_text())
    assert digest(freeze_path) == campaign["source_freeze_sha256"]
    for record in freeze["files"]:
        assert digest(ROOT / record["path"]) == record["sha256"], record["path"]
    rows = campaign["rows"]
    for row in rows:
        for kind in ["result", "verification"]:
            assert digest(ROOT / row[kind + "_path"]) == row[kind + "_sha256"]
    arms = {}
    for arm in "ABC":
        selected = [row for row in rows if row["arm"] == arm]
        arms[arm] = {
            "questions": len(selected),
            "accepted": sum(row["accepted"] for row in selected),
            "decisions": {v: sum(row["decision"] == v for row in selected)
                          for v in ["CONSISTENT", "CONFLICT", "INCOMPLETE"]},
            "wall_mean_seconds": statistics.mean(row["complete_service_wall_seconds"] for row in selected),
            "wall_median_seconds": statistics.median(row["complete_service_wall_seconds"] for row in selected),
            "wall_min_seconds": min(row["complete_service_wall_seconds"] for row in selected),
            "wall_max_seconds": max(row["complete_service_wall_seconds"] for row in selected),
            "cpu_mean_seconds": statistics.mean(row["inclusive_cpu_seconds"] for row in selected),
        }
    comparisons = {}
    for treatment, control in [("B", "A"), ("C", "A"), ("B", "C")]:
        matched = []
        for family in dict.fromkeys(row["family"] for row in rows):
            pair = {row["arm"]: row for row in rows if row["family"] == family}
            matched.append({"family": family,
                            "wall_difference_seconds": pair[treatment]["complete_service_wall_seconds"] - pair[control]["complete_service_wall_seconds"],
                            "cpu_difference_seconds": pair[treatment]["inclusive_cpu_seconds"] - pair[control]["inclusive_cpu_seconds"],
                            "same_decision": pair[treatment]["decision"] == pair[control]["decision"]})
        comparisons[treatment + "_minus_" + control] = {
            "pairs": matched,
            "wall_difference_mean_seconds": statistics.mean(x["wall_difference_seconds"] for x in matched),
            "cpu_difference_mean_seconds": statistics.mean(x["cpu_difference_seconds"] for x in matched),
            "treatment_faster_count": sum(x["wall_difference_seconds"] < 0 for x in matched),
            "additional_accepted_outcomes": arms[treatment]["accepted"] - arms[control]["accepted"],
        }
    summary = {"schema": "agi-alpha-second-investment-production-summary/v1",
               "campaign_sha256": digest(campaign_path),
               "source_freeze_sha256": digest(freeze_path),
               "arms": arms, "comparisons": comparisons,
               "new_customer_orders": 0,
               "human_minutes_saved": None, "customer_minutes_saved": None,
               "scope": "Six prospective-selected research substitutions, one run per arm; metadata contract only.",
               "limits": ["Single same-machine runs, shared cache and balanced order; no inferential speed or field reliability claim.",
                          "Two root-minimum conflicts were foreseeable from development inputs; they are not newly discovered upstream defects.",
                          "Independent checker and reviewer are separate assistant contributors in the same research environment, not external customer acceptance.",
                          "A includes study-only capture and acceptance instrumentation; no retained second enterprise capability is assumed.",
                          "The common verifier is measured in every arm; its research construction is not assumed free.",
                          "No human labor reduction, demand increase, additional eventual output, price premium or runtime qualification is demonstrated."]}
    summary_path = ROOT / "results/production-summary.json"
    save(summary_path, summary)
    with (ROOT / "results/production-measurements.csv").open("w", newline="") as stream:
        fields = ["mission", "family", "arm", "accepted", "decision", "complete_service_wall_seconds", "inclusive_cpu_seconds", "job_sha256", "result_sha256", "verification_sha256"]
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    native_paths = [x["path"] for x in freeze["files"] if x["path"].startswith("native/")]
    manifests = {}
    for arm, files in {
        "B": ["production/retained.py", "production/workbench.mjs", "production/verify.py", "protocol/acceptance-contract.json"] + native_paths,
        "C": ["production/conventional.py", "production/verify.py", "protocol/acceptance-contract.json"],
    }.items():
        path = ROOT / f"protocol/asset-{arm}.json"
        save(path, {"schema": "agi-alpha-second-investment-asset/v1", "arm": arm,
                    "authorship": "Assistant-researcher implementation; existing ordinary pip and packaging adopted. No autonomous invention claim.",
                    "source_freeze_sha256": digest(freeze_path),
                    "files": [{"path": name, "sha256": digest(ROOT / name)} for name in files]})
        manifests[arm] = digest(path)
    effect_arms = {}
    for arm in "BC":
        seconds = arms["A"]["cpu_mean_seconds"] - arms[arm]["cpu_mean_seconds"]
        microcents = seconds / 3600 * 100_000_000
        effect_arms[arm] = {
            "id": "full-lock-evidence-" + arm,
            "assetSHA256": manifests[arm],
            "acceptanceEvidenceSHA256": digest(campaign_path),
            "tested": True, "researchPrototypeConstructed": True,
            "effects": {"providerMinutesSaved": 0, "computeAndToolCentsSaved": 0, "customerReviewMinutesSaved": 0},
            "effectEvidence": {
                "providerMinutesSaved": "Unobserved active human effort. Credit zero incremental saving, not a measurement of zero human effort.",
                "computeAndToolCentsSaved": f"Matched inclusive CPU A minus {arm}: {seconds:.15g} seconds/job. At explicit $1/core-hour tariff this rounds to zero cents; the negative subcent residual is retained separately.",
                "customerReviewMinutesSaved": "No customer study or measured customer effort reduction. No price/demand uplift; same inherited service quality and buyer assumptions in all arms."},
            "unroundedComputeSavingsMicrocentsPerJob": round(microcents),
            "diagnostic_raw_compute_savings_microcents_per_job": microcents,
            "diagnostic_cpu_seconds_saved_per_job": seconds,
            "diagnostic_precision": "Nearest microcent, one microcent=USD0.00000001. This is a conditional arithmetic mapping, not an actual bill."}
    save(ROOT / "market/effect-profile.json", {
        "schema": "agi-alpha-second-investment-effect-profile/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_summary_sha256": digest(summary_path),
        "campaign_sha256": digest(campaign_path),
        "tariff": {"usd_per_core_hour": 1, "basis": "explicit scenario, not measured invoice or cloud price"},
        "rounding": "Cent-ledger effects are zero. Signed diagnostic microcents preserve measured slowdowns; they cannot change the no-benefit conclusion.",
        "arms": effect_arms})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Execute seeded development creator/challenge/revision/regression chains."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
from check import check
from challenge import challenge
from adjudicate import adjudicate, evidence_digest
from development_cases import plan, repair, calendar_dip, late_lock, mutation_cases

ROOT = Path(__file__).resolve().parent


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def main():
    mutations = {name:(env,code) for name,env,code in mutation_cases()}
    selected = [("calendar_overload", calendar_dip, "capacity"),
                ("moved_locked_prefix", repair, "locked_start"),
                ("unpropagated_locked_critical_path", late_lock, "bound_claim")]
    records, cost = [], 0
    for name, factory, finding_type in selected:
        original, _ = mutations[name]
        revised = factory()
        proposed = challenge(original["task"], original["result"])
        if finding_type == "bound_claim":
            digest, _ = evidence_digest(original["task"], original["result"])
            claim = dict(schema="release-plan-challenge/v1", id="review-derived-bound-objection",
                         type="bound_claim", evidence_digest=digest, witness=dict(field="critical"),
                         consequence="Ignoring a late fixed predecessor yields a false registered critical-path certificate.")
            origin = "reviewer-specified development objection; no claim of automatic bound-defect discovery"
        else:
            claim = next(c for c in proposed["challenges"] if c["type"] == finding_type)
            origin = "bounded automatic challenger reading original task and result"
        judgment = adjudicate(original["task"], original["result"], claim)
        final_check = check(revised)
        assert judgment["decision"] == "SUBSTANTIATED" and final_check["valid"] and final_check["qualified"]
        counts = dict(creator_output_bytes=len(canonical(original["result"])),
                      challenger=proposed["counts"]["total"], adjudication=judgment["counts"]["total"],
                      revision_output_bytes=len(canonical(revised["result"])),
                      regression_check=final_check["counts"]["total"])
        cost += sum(counts.values())
        records.append(dict(id=name, split="development", creator_origin="intentional seeded defective output, not an organic solver failure",
                            original=original, proposed_challenges=proposed, selected_challenge=claim,
                            challenge_origin=origin, adjudication=judgment,
                            revision=revised, regression_check=final_check, acquisition_reference_work=counts,
                            retained=True, inherited_proof=[], inherited_authority=[], protected_confirmation=False))
    e = plan()
    digest,_ = evidence_digest(e["task"], e["result"])
    false_claim = dict(schema="release-plan-challenge/v1", id="false-overlap-objection", type="capacity",
                       evidence_digest=digest, witness=dict(slot=0),
                       consequence="A deliberately false critic claims any overlap is forbidden.")
    rejected = adjudicate(e["task"], e["result"], false_claim)
    assert rejected["decision"] == "REFUTED"
    cost += rejected["counts"]["total"]
    false_record = dict(id="false_overlap_criticism", split="development", original=e,
                        creator_origin="correct hand-authored synthetic result",
                        challenge_origin="intentionally false criticism for adjudicator validation",
                        selected_challenge=false_claim, adjudication=rejected,
                        revision=None, retained_as_positive_failure=False,
                        retained_as_adjudicator_regression=True, protected_confirmation=False)
    out = dict(schema="release-plan-regression-assets/v1", purpose="development-only fault-injection evidence",
               claims_excluded=["organic defect discovery", "improvement in final correctness", "AGI-specific advantage", "commercial value"],
               assets=records, false_criticism=false_record, acquisition_reference_work=cost,
               provenance=dict(external_review=False, same_project_commission=True,
                               candidate_solver_imported=False, protected_confirmation_accessed=False))
    out["retained_file_bytes"] = 0
    out["acquisition_plus_retention_reference_work"] = cost
    for _ in range(8):
        encoded = (json.dumps(out, indent=2) + "\n").encode()
        if out["retained_file_bytes"] == len(encoded):
            break
        out["retained_file_bytes"] = len(encoded)
        out["acquisition_plus_retention_reference_work"] = cost + len(encoded)
    assert out["retained_file_bytes"] == len(encoded)
    path = ROOT / "regression_assets.json"
    path.write_bytes(encoded)
    print(json.dumps(dict(status="PASS", substantiated=len(records), false_criticisms_refuted=1,
                         revisions_independently_validated=len(records), acquisition_reference_work=cost,
                         retained_file_bytes=len(encoded), output=str(path)), indent=2))


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: Apache-2.0
"""Reproduce the five review findings using the exact prereview module and current fixture helpers."""

import json, tempfile, hashlib
from pathlib import Path
import test_flywheel_insight as t
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import Discovery
from alpha_factory_v1.core.runtime.successor.flywheel_insight import SearchReview, SearchAssessment
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import EvidenceRef

rows = []
for name, interpretation, amount in [
    ("control", "supports", 50),
    ("falsified", "falsifies", 50),
    ("inconclusive", "inconclusive", 50),
    ("underdeclared", "supports", 60),
    ("over-budget", "supports", 150),
]:
    with tempfile.TemporaryDirectory() as directory:
        state = t.f.setup.__wrapped__(Path(directory))
        result, sub, _, _ = t.constructed_assessment(state, interpretation, amount)
        rows.append(
            {
                "case": name,
                "original_disposition": result["disposition"],
                "known_cost_micro_usd": amount,
                "declared_cost_micro_usd": 50,
                "cap_micro_usd": 100,
                "last_interpretation": interpretation,
                "authority_granted": result["authority_granted"],
            }
        )
with tempfile.TemporaryDirectory() as directory:
    state = t.f.setup.__wrapped__(Path(directory))
    protocol = t.freeze(state)
    t.apply(state, "search-freeze", protocol, "freeze")
    sub = t.apply(state, "search-submit", t.submission(state, protocol), "submit")
    ref = EvidenceRef(journal_key=sub["id"], record_digest=sub["digest"])
    refs = []
    for i in range(17):
        term = SearchReview(
            review_id=f"r-{i}",
            submission=ref,
            reviewer_id=f"reviewer-{i}",
            dimension="novelty",
            score=1,
            rationale="Original-source bounded inventory probe",
            evidence=[protocol.sources[0].evidence],
            review_relationship="same-operator",
            limitations="Fixture only",
        )
        review = t.apply(state, "search-review", term, f"r-{i}")
        refs.append(EvidenceRef(journal_key=review["id"], record_digest=review["digest"]))
    refused = False
    try:
        SearchAssessment(
            assessment_id="all",
            submission=ref,
            reviews=refs,
            construction_observation=None,
            leakage_audit=None,
            leakage_disposition="unassessed",
            limitations="Fixture",
        )
    except ValueError:
        refused = True
    rows.append({"case": "review-cap", "accepted_reviews": len(refs), "assessment_with_all_reviews_refused": refused})
assert rows[0]["original_disposition"] == "bounded-discovery-candidate"
assert all(row["original_disposition"] == "bounded-discovery-candidate" for row in rows[1:5])
assert rows[-1]["accepted_reviews"] == 17 and rows[-1]["assessment_with_all_reviews_refused"]
from alpha_factory_v1.core.runtime.successor import flywheel_insight as original_module

source = Path(original_module.__file__)
assert (
    hashlib.sha256(source.read_bytes()).hexdigest()
    == "6aa7c34b3e45a7226d18e7f6a65c31091cdd3b0686e2e4fe70bb123f29798950"
)
print(
    json.dumps(
        {
            "source_commit": "5d89b4ccfd0622433a46f8952285c7b291baf928",
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "scope": "Explicitly fictional local conformance, not model or market performance",
            "confirmed_violations": 5,
            "valid_positive_controls": 1,
            "rows": rows,
        },
        indent=2,
    )
)

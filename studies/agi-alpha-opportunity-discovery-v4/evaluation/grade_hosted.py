# SPDX-License-Identifier: Apache-2.0
"""Record one independent adjudication of the three unchanged hosted answers."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
EXPERTISE = ROOT.parent / "expertise"
EXPECTED_ANSWERS = {
    "U": "9692e281021b7316c8bf8e681e1432351a6d10cb4a7e1a830c918e8b44c12127",
    "E": "196a7c16c4ddb6c3d3b7949bd41199613dfaeba860a9e2d185f6e5bca81fe3ed",
    "Eplus": "2c36ecb7716cc49c9ff807de58625c0b49e523b32f13690cc214a58f70252e94",
}
LINES = {
    "U": {
        "H1": [[7], [3], [5, 7, 9], [13, 14, 15], [5, 19], [19]],
        "H2": [[25], [23, 25], [23, 25], [27], [29], [29]],
        "H3": [[33, 37, 38, 44], [44, 46], [50, 54, 56], [51, 52], [53, 54], [54, 56]],
        "H4": [[64, 65], [66, 67, 68], [69, 70], [64, 69, 70, 74], [65, 72], [74, 76, 78]],
    },
    "E": {
        "H1": [[9], [5], [7, 11, 12], [11, 12], [12, 14], [14]],
        "H2": [[20], [20, 22], [20, 22], [22], [18, 24], [24]],
        "H3": [[32, 33, 37], [37, 39], [43, 44, 47], [45], [45, 46], [43, 47]],
        "H4": [[53], [54], [55], [53, 55], [53], [57, 59]],
    },
    "Eplus": {
        "H1": [[7], [5], [7, 9], [13, 14, 15], [7, 17], [19]],
        "H2": [[23, 25], [23, 25], [25], [27], [27], [29]],
        "H3": [[37, 38, 44], [44, 46], [33, 50, 51], [52], [53, 54], [50, 54]],
        "H4": [[62], [63], [64, 68], [62, 64], [62], [66, 68]],
    },
}
REASONS = {
    "H1": [
        "Formal metre default and explicit receiving units distinguished; reinterpretation remains hypothetical.",
        "Destination interval resolved from target plus signed deviations.",
        "All 76 values accounted for; formal and hypothetical universal claims both refuted.",
        "Concrete source actual IDs and scaled values recover real counterexamples.",
        "Supplier PASS applies to its broader interval.",
        "Remaining feature, specimen, requirement, measurement and authority conditions are stated.",
    ],
    "H2": [
        "Twenty qualifying source items and 400 actuals identified.",
        "Exact receiving interval and selected observed range are correct.",
        "All 400 satisfy the scalar interval under the explicit hypothesis.",
        "Permutation argument concerns a universal common predicate, not invented pairwise mapping.",
        "Particular physical hole identification from the family result is denied.",
        "Coverage, specimen, semantics, metrology and authority remain conditions.",
    ],
    "H3": [
        "Different exact hashes and the concrete empty-list difference are identified.",
        "No numerical change or false-graph conclusion inferred merely from byte drift.",
        "Old qualification remains scoped; current mission requalification is required.",
        "Owner-authorized unit evidence or corrected export requested; no automatic conversion.",
        "Acquisition plan addresses mappings, specimens, requirements and metrology.",
        "Current authorization remains separate from inherited proof.",
    ],
    "H4": [
        "Actual 534, item 33, nominal 32, definition 31 and 3.314 mm recovered.",
        "Actual feature 533, item 29, nominal 28 and definition 27 recovered.",
        "Result 604 and the full specimen serial recovered without conflicting identification.",
        "Local PASS and parent FAIL remain separate.",
        "3.314 mm checked against the 3.1–3.5 mm interval.",
        "Incoming association is distinguished from FAIR identity, physical release and causality.",
    ],
}


def sha(path: Path) -> str:
    """Hash the precise adjudicated artifact."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Save each criterion and resource limitation without answer correction."""
    freeze = json.loads((EXPERTISE / "freeze.json").read_text())
    for name, expected in freeze["files"].items():
        if sha(ROOT.parent / name) != expected:
            raise ValueError("hosted protocol/rubric drift: " + name)
    rubric_path = ROOT / "protected" / "oracles" / "hosted_rubric.json"
    rubric = json.loads(rubric_path.read_text())
    output = ROOT / "hosted-grading-v1"
    output.mkdir(exist_ok=False)
    summaries = []
    for arm in ["U", "E", "Eplus"]:
        answer_path = EXPERTISE / arm / "answer.md"
        if sha(answer_path) != EXPECTED_ANSWERS[arm]:
            raise ValueError("answer changed after single adjudication: " + arm)
        answer = answer_path.read_text()
        resource_path = EXPERTISE / arm / ("resource_log.json" if arm == "U" else "resources.json")
        resources = json.loads(resource_path.read_text())
        call_key = {"U": "tool_calls", "E": "tool_call_turns", "Eplus": "top_level_tool_calls"}[arm]
        calls = resources[call_key]
        jobs: list[dict[str, Any]] = []
        for job in rubric["jobs"]:
            jid = job["id"]
            criteria = []
            for index, requirement in enumerate(job["mandatory"]):
                passed = not (arm == "Eplus" and jid == "H4" and index == 2)
                reason = REASONS[jid][index]
                if not passed:
                    reason = (
                        "Line 64 correctly gives component ID 528 and the full specimen serial. "
                        "Line 68 then directs the operator to verify 'serial 528’s specimen'. "
                        "528 is a file-local component ID, not that serial. The contradictory actionable "
                        "identifier fails exact, unambiguous specimen recovery. No new fatal category is added."
                    )
                criteria.append(
                    {
                        "criterion_id": f"{jid}.{index + 1}",
                        "criterion": requirement,
                        "passed": passed,
                        "evidence_answer_lines": LINES[arm][jid][index],
                        "reason": reason,
                    }
                )
            jobs.append(
                {
                    "job_id": jid,
                    "accepted": all(c["passed"] for c in criteria),
                    "mandatory_passes": sum(c["passed"] for c in criteria),
                    "mandatory_total": len(criteria),
                    "criteria": criteria,
                    "fatal_errors": [],
                }
            )
        receipt = {
            "arm": arm,
            "answer_sha256": sha(answer_path),
            "resource_record_sha256": sha(resource_path),
            "answer_words_whitespace": len(answer.split()),
            "word_budget_met": len(answer.split()) <= 1600,
            "tool_calls_self_reported": calls,
            "tool_budget_met_from_self_report": calls <= 8,
            "tool_count_independently_reconstructed": False,
            "accepted_jobs": sum(j["accepted"] for j in jobs),
            "total_jobs": 4,
            "mandatory_criteria_passed": sum(j["mandatory_passes"] for j in jobs),
            "mandatory_criteria_total": 24,
            "jobs": jobs,
            "resource_self_report": resources,
            "complete_cost": None,
            "billing": None,
            "inference_tokens": None,
            "active_model_latency_seconds": None,
            "customer_effort_observed": None,
        }
        (output / f"{arm}.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        keys = [
            "arm", "answer_sha256", "accepted_jobs", "total_jobs", "mandatory_criteria_passed",
            "mandatory_criteria_total", "tool_calls_self_reported", "answer_words_whitespace", "complete_cost",
        ]
        summaries.append({key: receipt[key] for key in keys})
    summary = {
        "schema": "hosted-rubric-evaluation-v1",
        "graded_utc": dt.datetime.now(dt.UTC).isoformat(),
        "frozen_rubric_sha256": sha(rubric_path),
        "expertise_freeze_sha256": sha(EXPERTISE / "freeze.json"),
        "grading_script_sha256": sha(Path(__file__)),
        "method": (
            "Independent AI-assisted adjudication against unchanged mandatory criteria and fatal-error list, "
            "with answer-line evidence. Exact identifiers must remain unambiguous across an actionable answer."
        ),
        "rows": summaries,
        "findings": [
            "U 4/4 and E 4/4: no accepted-quality improvement established by E versus U in this packet.",
            "Eplus 3/4 under strict exact-identifier criterion: no additional learned Alpha established.",
            "Calls U 7 / E 6 / Eplus 8 are self-reported resource counts, not complete costs or causal efficiency estimates.",
            "All answers meet the common 1,600-word ceiling; all self-report at most 8 tools.",
            "One trial per arm on four correlated historical-source jobs cannot establish population superiority or method-caused harm.",
        ],
        "criterion_H4_3_application": (
            "The enhanced answer states the correct full serial once but later uses the component ID as a serial "
            "in its requested next action. Strict complete acceptance requires resolving that conflict; it was not corrected."
        ),
        "nonprimary_lenient_reading": (
            "If the correct table entry alone were sufficient and the conflicting action ignored, Eplus would be 4/4. "
            "That is not the exact-identifier acceptance applied here; either reading establishes no additional accepted-quality gain."
        ),
        "new_fatal_categories_added": False,
        "actual_collections": 0,
        "actual_complete_cost": None,
        "no_answer_revisions": True,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()

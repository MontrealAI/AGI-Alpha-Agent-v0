# SPDX-License-Identifier: Apache-2.0
"""Post-seal aggregation over the unchanged frozen mechanical scorer."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scorer import all_refs, covers_quote, score


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_change_coverage(case: dict[str, Any], packet: dict[str, Any]) -> tuple[int, int]:
    coverage: dict[str, set[int]] = {"original": set(), "revised": set()}
    for change in packet.get("changes", []):
        for field, document in (("original_span", "original"), ("revised_span", "revised")):
            ref = change.get(field)
            if (
                isinstance(ref, dict)
                and ref.get("document") == document
                and type(ref.get("start")) is int
                and type(ref.get("end")) is int
            ):
                coverage[document].update(range(ref["start"], ref["end"]))
    missing, total = 0, 0
    for kind, a, b, c, d in difflib.SequenceMatcher(
        a=case["original_text"], b=case["revised_text"], autojunk=False
    ).get_opcodes():
        if kind != "equal":
            total += b - a + d - c
            missing += sum(i not in coverage["original"] for i in range(a, b))
            missing += sum(i not in coverage["revised"] for i in range(c, d))
    return missing, total


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def total(name: str) -> int:
        return sum(int(row[name]) for row in rows)

    return {
        "cases": len(rows),
        "accepted_deterministic": total("accepted_deterministic"),
        "missing_packets": total("missing_packet"),
        "rules_correct": total("rules_correct"),
        "rules_total": total("rules_total"),
        "weighted_status_error": total("weighted_status_error"),
        "weighted_status_possible": total("weighted_status_possible"),
        "false_passes": total("false_passes"),
        "severity5_false_passes": total("severity5_false_passes"),
        "false_positive_deviations": total("false_positives"),
        "required_support_passages": total("required_support_passages"),
        "covered_support_passages": total("covered_support_passages"),
        "required_obligation_passages": total("required_obligation_passages"),
        "covered_obligation_passages": total("covered_obligation_passages"),
        "uncertain_absent_expected": total("uncertain_absent_expected"),
        "uncertain_absent_correctly_escalated": total("uncertain_absent_correctly_escalated"),
        "references_checked": total("references_checked"),
        "invalid_references": total("invalid_references"),
        "changed_characters": total("changed_characters"),
        "missing_changed_characters": total("missing_changed_characters"),
        "strict_missing_changed_characters": total("strict_missing_changed_characters"),
        "accepted_but_strict_change_coverage_failed": sum(
            row["accepted_deterministic"] and row["strict_missing_changed_characters"] > 0 for row in rows
        ),
        "proposed_revisions": total("proposed_revision_count"),
        "unsupported_revisions": total("unsupported_revision_count"),
        "professionally_accepted": 0,
        "professional_acceptance": "NOT_ASSESSED",
    }


def audit(root: Path, cohorts: list[str], arms: list[str]) -> dict[str, Any]:
    freeze = json.loads((root / "protocol/production-freeze.json").read_text())
    corpus = json.loads((root / "protocol/corpus-freeze.json").read_text())
    for binding in freeze["files"]:
        path = root / binding["path"]
        if sha(path) != binding["sha256"] or path.stat().st_size != binding["bytes"]:
            raise ValueError("Frozen source identity mismatch: " + binding["path"])
    by_case = {row["case_id"]: row for row in corpus["cases"]}
    records, readbacks = [], []
    for cohort in cohorts:
        cases = sorted((root / "inputs" / cohort).glob("*.json"))
        if not cases:
            raise ValueError("No declared cases for cohort " + cohort)
        for case_path in cases:
            case = json.loads(case_path.read_text())
            binding = by_case[case["case_id"]]
            key_path = root / binding["key_path"]
            if sha(case_path) != binding["input_sha256"] or sha(key_path) != binding["key_sha256"]:
                raise ValueError("Frozen corpus/key identity mismatch: " + case["case_id"])
            key = json.loads(key_path.read_text())
            for arm in arms:
                path = root / "evidence" / cohort / case["case_id"] / arm / "produced.json"
                if path.exists():
                    envelope = json.loads(path.read_text())
                    if envelope["request"] != case or envelope["arm"] != arm:
                        raise ValueError("Produced input/arm identity mismatch: " + str(path))
                    packet = {**envelope["packet"], "arm": arm}
                    readbacks.append({"path": str(path.relative_to(root)), "sha256": sha(path)})
                else:
                    packet = {"case_id": case["case_id"], "arm": arm}
                result = score(case, packet, key)
                result["cohort"] = cohort
                result["missing_packet"] = not path.exists()
                result["produced_path"] = str(path.relative_to(root))
                result["strict_missing_changed_characters"], result["strict_changed_characters"] = (
                    strict_change_coverage(case, packet)
                )
                rules = {row["rule_id"]: row for row in packet.get("rule_results", [])}
                supports = key.get("required_sources", [])
                obligations = [s for s in supports if s.get("kind") == "obligation"]
                result["required_support_passages"] = len(supports)
                result["covered_support_passages"] = sum(
                    covers_quote(rules.get(s["rule_id"], {}).get("sources", []), s) for s in supports
                )
                result["required_obligation_passages"] = len(obligations)
                result["covered_obligation_passages"] = sum(
                    covers_quote(all_refs(packet.get("obligations", [])), s) for s in obligations
                )
                expected_uncertain = [
                    rid for rid, status in key["expected_statuses"].items() if status in {"uncertain", "absent"}
                ]
                codes = {e.get("code") for e in packet.get("escalations", [])}
                codes.update(e.get("rule_id") for e in packet.get("escalations", []))
                result["uncertain_absent_expected"] = len(expected_uncertain)
                result["uncertain_absent_correctly_escalated"] = sum(
                    rules.get(rid, {}).get("status") == key["expected_statuses"][rid] and rid in codes
                    for rid in expected_uncertain
                )
                result["proposed_revision_count"] = len(packet.get("proposed_revisions", []))
                result["unsupported_revision_count"] = sum(
                    issue["type"] == "unsupported_revision" for issue in result["issues"]
                )
                records.append(result)
    summaries = {
        cohort: {arm: aggregate([r for r in records if r["cohort"] == cohort and r["arm"] == arm]) for arm in arms}
        for cohort in cohorts
    }
    return {
        "schema": "independent-legal-mechanical-audit/v1",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "source_freeze_sha256": sha(root / "protocol/production-freeze.json"),
        "corpus_freeze_sha256": sha(root / "protocol/corpus-freeze.json"),
        "scorer_sha256": sha(Path(__file__).with_name("scorer.py")),
        "summarizer_sha256": sha(Path(__file__)),
        "summary_status": "Post-seal descriptive aggregation; frozen scorer acceptance unchanged",
        "supplementary_change_check": "Document-scoped independent changed-character audit; does not allow amendment spans to cover revised-document offsets. This reports a known frozen-scorer limitation without changing primary acceptance.",
        "professional_evaluation": "Unavailable; no professional legal acceptance inferred",
        "summaries": summaries,
        "records": records,
        "prediction_readbacks": readbacks,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--cohorts", nargs="+", default=["primary", "stress"])
    parser.add_argument("--arms", nargs="+", default=["B", "C1", "C", "D"])
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.root, args.cohorts, args.arms)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result["summaries"], indent=2))

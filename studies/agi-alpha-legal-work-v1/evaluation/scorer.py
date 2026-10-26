# SPDX-License-Identifier: Apache-2.0
"""Mechanical source and authored-key scoring; no legal assessment."""

from __future__ import annotations

import difflib
import hashlib
from typing import Any

RULES = (
    "R1_PURPOSE",
    "R2_CONFIDENTIALITY_TERM",
    "R3_RETURN_DEADLINE",
    "R4_COMPELLED_NOTICE",
    "R5_RESIDUALS",
    "R6_ASSIGNMENT",
    "R7_GOVERNING_LAW",
    "R8_REPRESENTATIVES",
)


def document_map(case: dict[str, Any]) -> dict[str, str]:
    docs = {"original": case["original_text"], "revised": case["revised_text"]}
    docs.update({"amendment:" + a["id"]: a["text"] for a in case.get("amendments", [])})
    return docs


def all_refs(value: Any) -> list[dict[str, Any]]:
    result = []
    if isinstance(value, dict):
        if all(k in value for k in ("document", "start", "end", "quote")):
            result.append(value)
        else:
            for child in value.values():
                result.extend(all_refs(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(all_refs(child))
    return result


def ref_valid(ref: dict[str, Any], docs: dict[str, str]) -> bool:
    name, start, end = ref.get("document"), ref.get("start"), ref.get("end")
    if name not in docs or type(start) is not int or type(end) is not int:
        return False
    text = docs[name]
    return 0 <= start <= end <= len(text) and ref.get("quote") == text[start:end]


def covers_quote(refs: list[dict[str, Any]], requirement: dict[str, Any]) -> bool:
    return any(
        r.get("document") == requirement["document"] and requirement["quote"] in r.get("quote", "") for r in refs
    )


def changed_coverage(case: dict[str, Any], packet: dict[str, Any]) -> tuple[int, int]:
    coverage: dict[str, set[int]] = {"original": set(), "revised": set()}
    for change in packet.get("changes", []):
        for field, name in (("original_span", "original"), ("revised_span", "revised")):
            ref = change.get(field)
            if isinstance(ref, dict) and type(ref.get("start")) is int and type(ref.get("end")) is int:
                coverage[name].update(range(ref["start"], ref["end"]))
    missing, total = 0, 0
    for kind, a, b, c, d in difflib.SequenceMatcher(
        a=case["original_text"], b=case["revised_text"], autojunk=False
    ).get_opcodes():
        if kind == "equal":
            continue
        for name, start, end in (("original", a, b), ("revised", c, d)):
            total += end - start
            missing += sum(x not in coverage[name] for x in range(start, end))
    return missing, total


def score(case: dict[str, Any], packet: dict[str, Any], key: dict[str, Any]) -> dict[str, Any]:
    issues = []
    docs = document_map(case)
    if packet.get("case_id") != case["case_id"]:
        issues.append({"type": "identity", "detail": "case_id mismatch", "weight": 5})
    expected_hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in docs.items()}
    if packet.get("source_hashes") != expected_hashes:
        issues.append({"type": "source_hashes", "detail": "source hashes differ or omit an input", "weight": 5})
    refs = all_refs(packet)
    invalid = [r for r in refs if not ref_valid(r, docs)]
    if invalid:
        issues.append(
            {"type": "invalid_sources", "detail": f"{len(invalid)} references are not exact source spans", "weight": 5}
        )
    rows = packet.get("rule_results", [])
    ids = [row.get("rule_id") for row in rows]
    if len(rows) != len(RULES) or set(ids) != set(RULES) or len(set(ids)) != len(ids):
        issues.append(
            {"type": "rule_inventory", "detail": "rule inventory is missing, duplicated or unexpected", "weight": 5}
        )
    by_id = {row.get("rule_id"): row for row in rows}
    comparisons = []
    for rule in RULES:
        expected = key["expected_statuses"][rule]
        observed = by_id.get(rule, {}).get("status", "missing")
        severity = 3 if rule in {"R6_ASSIGNMENT", "R8_REPRESENTATIVES"} else 5
        comparisons.append(
            {
                "rule_id": rule,
                "expected": expected,
                "observed": observed,
                "severity": severity,
                "correct": observed == expected,
            }
        )
        if observed != expected:
            issues.append(
                {
                    "type": "status_mismatch",
                    "rule_id": rule,
                    "expected": expected,
                    "observed": observed,
                    "weight": severity,
                }
            )
    for requirement in key.get("required_sources", []):
        sources = by_id.get(requirement["rule_id"], {}).get("sources", [])
        if not covers_quote(sources, requirement):
            issues.append(
                {
                    "type": "missing_material_source",
                    "rule_id": requirement["rule_id"],
                    "document": requirement["document"],
                    "quote": requirement["quote"],
                    "weight": requirement.get("severity", 5),
                }
            )
        if requirement.get("kind") == "obligation" and not covers_quote(
            all_refs(packet.get("obligations", [])), requirement
        ):
            issues.append(
                {
                    "type": "missing_obligation",
                    "rule_id": requirement["rule_id"],
                    "quote": requirement["quote"],
                    "weight": requirement.get("severity", 5),
                }
            )
    missing_chars, changed_chars = changed_coverage(case, packet)
    if missing_chars:
        issues.append(
            {
                "type": "incomplete_changes",
                "detail": f"{missing_chars}/{changed_chars} changed source characters omitted",
                "weight": 5,
            }
        )
    if packet.get("supported_scope") is not key["supported_scope"]:
        issues.append({"type": "scope", "detail": "supported_scope mismatch", "weight": 5})
    codes = {x.get("code") for x in packet.get("escalations", [])}
    codes.update(x.get("rule_id") for x in packet.get("escalations", []))
    for needed in key.get("required_escalation_codes", []) + key.get("required_escalation_rules", []):
        if needed not in codes:
            issues.append({"type": "missing_escalation", "detail": needed, "weight": 5})
    for revision in packet.get("proposed_revisions", []):
        restorations = [r for r in all_refs(revision) if r.get("document") == "original" and ref_valid(r, docs)]
        text = revision.get("text", revision.get("proposed_text"))
        if (
            not restorations
            or text not in [r["quote"] for r in restorations]
            or not revision.get("requires_counsel_approval")
        ):
            issues.append(
                {
                    "type": "unsupported_revision",
                    "detail": "revision is not an exact conditional original-clause restoration",
                    "weight": 5,
                }
            )
    if packet.get("professional_acceptance") != "unknown":
        issues.append(
            {"type": "professional_claim", "detail": "professional acceptance must remain unknown", "weight": 5}
        )
    if packet.get("legal_advice") or packet.get("recommended_execution"):
        issues.append(
            {
                "type": "unsupported_legal_action",
                "detail": "packet includes an unsupported legal-advice/execution field",
                "weight": 5,
            }
        )
    false_passes = [c for c in comparisons if c["observed"] == "pass" and c["expected"] != "pass"]
    false_positives = [c for c in comparisons if c["observed"] == "deviation" and c["expected"] == "pass"]
    accepted = not issues
    return {
        "case_id": case["case_id"],
        "arm": packet.get("arm"),
        "stratum": key.get("stratum"),
        "accepted_deterministic": accepted,
        "professional_acceptance": "unknown",
        "completed_support_packet": accepted and key["supported_scope"],
        "escalation_required": bool(packet.get("escalations")),
        "rule_comparisons": comparisons,
        "rules_correct": sum(c["correct"] for c in comparisons),
        "rules_total": len(RULES),
        "weighted_status_error": sum(c["severity"] for c in comparisons if not c["correct"]),
        "weighted_status_possible": 36,
        "false_passes": len(false_passes),
        "severity5_false_passes": sum(c["severity"] == 5 for c in false_passes),
        "false_positives": len(false_positives),
        "references_checked": len(refs),
        "invalid_references": len(invalid),
        "changed_characters": changed_chars,
        "missing_changed_characters": missing_chars,
        "issues": issues,
    }

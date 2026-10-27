# SPDX-License-Identifier: Apache-2.0
"""Independent conservation checker with no diff algorithm or legal interpretation."""

from __future__ import annotations

import hashlib
from typing import Any


def check(case: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    expected_documents = {"original": case["original_text"], "revised": case["revised_text"]}
    for amendment in case.get("amendments", []):
        name = "amendment:" + amendment["id"]
        if name in expected_documents:
            raise ValueError("Duplicate input amendment identity")
        expected_documents[name] = amendment["text"]
    expected_hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in expected_documents.items()}
    if packet.get("case_id") != case["case_id"]:
        issues.append("CASE_IDENTITY")
    if packet.get("schema") != "legal-reconciliation/v1":
        issues.append("SCHEMA")
    if packet.get("documents") != expected_documents:
        issues.append("ORIGINAL_INPUT_BINDING")
    if packet.get("source_hashes") != expected_hashes:
        issues.append("ORIGINAL_SOURCE_HASHES")
    positions = {"original": 0, "revised": 0}
    reconstructed: dict[str, list[str]] = {"original": [], "revised": []}
    valid_spans = 0
    unchanged_codepoints = 0
    highlighted_codepoints = {"original": 0, "revised": 0}
    operations = packet.get("operations")
    if not isinstance(operations, list):
        operations = []
        issues.append("OPERATIONS_SCHEMA")
    for operation in operations:
        if not isinstance(operation, dict):
            issues.append("OPERATION_SCHEMA")
            continue
        quotes: dict[str, str] = {}
        valid_operation = True
        for name, position in positions.items():
            ref = operation.get(name + "_span")
            if not isinstance(ref, dict):
                issues.append("SPAN_SCHEMA")
                valid_operation = False
                continue
            start, end, quote = ref.get("start"), ref.get("end"), ref.get("quote")
            text = expected_documents[name]
            if (
                ref.get("document") != name
                or type(start) is not int
                or type(end) is not int
                or not 0 <= start <= end <= len(text)
                or not isinstance(quote, str)
                or quote != text[start:end]
            ):
                issues.append("SOURCE_SPAN")
                valid_operation = False
                continue
            if start != position:
                issues.append("GAP_OVERLAP_OR_REORDERING")
            positions[name] = end
            reconstructed[name].append(quote)
            quotes[name] = quote
            valid_spans += 1
        kind = operation.get("kind")
        if not isinstance(kind, str) or kind not in {"equal", "replace", "insert", "delete"}:
            issues.append("OPERATION_KIND")
        elif valid_operation:
            old, new = quotes["original"], quotes["revised"]
            valid_meaning = {
                "equal": old == new and bool(old),
                "replace": bool(old) and bool(new) and old != new,
                "insert": not old and bool(new),
                "delete": bool(old) and not new,
            }[kind]
            if not valid_meaning:
                issues.append("FALSE_OPERATION_LABEL")
            elif kind == "equal":
                unchanged_codepoints += len(old)
            else:
                highlighted_codepoints["original"] += len(old)
                highlighted_codepoints["revised"] += len(new)
    reconstructed_text = {name: "".join(parts) for name, parts in reconstructed.items()}
    for name, position in positions.items():
        if position != len(expected_documents[name]) or reconstructed_text[name] != expected_documents[name]:
            issues.append("INCOMPLETE_RECONSTRUCTION")
    amendment_names = {name for name in expected_documents if name.startswith("amendment:")}
    amendment_rows = packet.get("amendments")
    if not isinstance(amendment_rows, list):
        amendment_rows = []
        issues.append("AMENDMENT_SCHEMA")
    if (
        len(amendment_rows) != len(amendment_names)
        or {row["document"] for row in amendment_rows if isinstance(row, dict) and isinstance(row.get("document"), str)}
        != amendment_names
    ):
        issues.append("AMENDMENT_INVENTORY")
    for row in amendment_rows:
        document = row.get("document") if isinstance(row, dict) else None
        if (
            not isinstance(row, dict)
            or not isinstance(document, str)
            or document not in amendment_names
            or row.get("quote") != expected_documents.get(document)
            or row.get("effect") != "NOT_INTERPRETED"
        ):
            issues.append("AMENDMENT_CHANGED_OR_INTERPRETED")
    if (
        packet.get("decision") != "TEXT_RECONCILIATION_ONLY"
        or packet.get("professional_acceptance") != "unknown"
        or packet.get("legal_or_playbook_conclusions") != []
        or packet.get("proposed_revisions") != []
    ):
        issues.append("SEMANTIC_OR_PROFESSIONAL_SCOPE")
    return {
        "case_id": case["case_id"],
        "method": packet.get("method"),
        "accepted_independent": not issues,
        "issues": sorted(set(issues)),
        "valid_spans": valid_spans,
        "operations": len(operations),
        "changed_operations": sum(isinstance(op, dict) and op.get("kind") != "equal" for op in operations),
        "original_codepoints": len(expected_documents["original"]),
        "revised_codepoints": len(expected_documents["revised"]),
        "unchanged_codepoints": unchanged_codepoints,
        "highlighted_original_codepoints": highlighted_codepoints["original"],
        "highlighted_revised_codepoints": highlighted_codepoints["revised"],
        "preserved_context_ratio": {
            name: unchanged_codepoints / len(text) if text else 1.0
            for name, text in expected_documents.items()
            if name in positions
        },
        "localization_assessed": False,
        "amendments_preserved": len(amendment_names) if not any("AMENDMENT" in issue for issue in issues) else 0,
        "original_reconstructed_sha256": hashlib.sha256(reconstructed_text["original"].encode()).hexdigest(),
        "revised_reconstructed_sha256": hashlib.sha256(reconstructed_text["revised"].encode()).hexdigest(),
        "professional_acceptance": "unknown",
        "scope": "Exact text reconciliation only; no legal/playbook/meaning conclusions tested or inferred.",
    }

# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re
from typing import Any


def resolve_context(
    selected: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    by_section: dict[str, list[dict[str, Any]]] = {}
    definitions: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["id"]:
            by_section.setdefault(row["id"], []).append(row)
        text = row["source"]["quote"]
        for match in re.finditer(r'["“]([^"”]{2,80})["”]\s+(?:means|shall mean|is defined as)\b', text, re.IGNORECASE):
            definitions.setdefault(match.group(1).lower(), []).append(row)
    result: list[dict[str, Any]] = []
    visited = set()
    active = set()
    unresolved = []

    def visit(row: dict[str, Any], depth: int = 0) -> None:
        source = row["source"]
        identity = (source["document"], source["start"], source["end"])
        if identity in active:
            unresolved.append("Cyclic explicit source reference.")
            return
        if identity in visited:
            return
        if depth > 8:
            unresolved.append("Reference depth exceeds eight.")
            return
        active.add(identity)
        visited.add(identity)
        result.append(row)
        text = source["quote"]
        targets = []
        for match in re.finditer(r"\b(?:Section|Clause|Article)\s+(\d+(?:\.\d+)*(?:\([a-z]\))?)", text, re.IGNORECASE):
            target = match.group(1).rstrip(".")
            if row["id"] == target and match.start() < 12:
                continue
            options = by_section.get(target, [])
            if len(options) != 1:
                unresolved.append("Missing or duplicate section " + target)
            else:
                targets.append(options[0])
        for term, options in definitions.items():
            if term in text.lower() and row not in options:
                if len(options) != 1:
                    unresolved.append("Ambiguous definition: " + term)
                else:
                    targets.append(options[0])
        for match in re.finditer(
            r"\b(?:for|within|during)\s+(?:the\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2}\s+Period)\b", text
        ):
            term = match.group(1).lower()
            if term not in definitions and not re.search(r"\d\s*(?:months?|days?|years?)", text, re.IGNORECASE):
                unresolved.append("Undefined named period: " + match.group(1))
        for target in targets:
            visit(target, depth + 1)
        active.remove(identity)

    for row in selected:
        visit(row)
    return result, sorted(set(unresolved))

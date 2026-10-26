# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re
from typing import Any


def apply_explicit_amendments(
    case: dict[str, Any], rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    result = list(rows)
    superseded = []
    issues = []
    replaced: set[str] = set()
    for amendment in case["amendments"]:
        text = amendment["text"]
        document = "amendment:" + amendment["id"]
        source = {"document": document, "start": 0, "end": len(text), "quote": text}
        precedence = bool(re.search(r"\b(prevails|shall prevail|takes precedence|supersedes)\b", text, re.IGNORECASE))
        matches = list(
            re.finditer(
                r'(?:Section|Clause|Article)\s+(\d+(?:\.\d+)*(?:\([a-z]\))?)\s+(?:is|shall be)\s+(?:hereby\s+)?(?:deleted and replaced|replaced)(?:\s+in its entirety)?\s+(?:with|by|as follows)\s*:\s*["“]([\s\S]+?)["”]',
                text,
                re.IGNORECASE,
            )
        )
        remainder = text
        for match in reversed(matches):
            remainder = remainder[: match.start()] + remainder[match.end() :]
        remainder = re.sub(r"(?im)^\s*AMENDMENT[^\n]*SYNTHETIC\s*$", "", remainder)
        remainder = re.sub(
            r"(?i)This amendment (?:prevails|shall prevail|takes precedence|supersedes)[^.\n]*(?:\.|$)", "", remainder
        )
        unsupported = bool(re.sub(r"[\s.;,:]+", "", remainder))
        if not precedence or not matches or unsupported:
            issues.append(
                {
                    "code": "AMENDMENT_UNRESOLVED",
                    "detail": "Only express precedence and quoted whole-section replacement are supported.",
                    "sources": [source],
                }
            )
            continue
        local_result = list(result)
        local_superseded = []
        local_targets: set[str] = set()
        failed = False
        for match in matches:
            target = match.group(1)
            prior = [row for row in local_result if row["id"] == target]
            if len(prior) != 1 or target in replaced or target in local_targets:
                failed = True
                issues.append(
                    {
                        "code": "AMENDMENT_CONFLICT",
                        "detail": "Missing, duplicated or multiply amended target section " + target,
                        "sources": [source],
                    }
                )
                break
            local_targets.add(target)
            replacement = {
                "id": target,
                "source": {"document": document, "start": match.start(2), "end": match.end(2), "quote": match.group(2)},
            }
            local_result = [replacement if row is prior[0] else row for row in local_result]
            local_superseded.append(
                {
                    "target": target,
                    "original_source": prior[0]["source"],
                    "replacement_source": replacement["source"],
                    "authority_source": source,
                    "scope": "Mechanical explicit replacement; legal validity unassessed",
                }
            )
        if not failed:
            result = local_result
            superseded.extend(local_superseded)
            replaced.update(item["target"] for item in local_superseded)
    return result, superseded, issues

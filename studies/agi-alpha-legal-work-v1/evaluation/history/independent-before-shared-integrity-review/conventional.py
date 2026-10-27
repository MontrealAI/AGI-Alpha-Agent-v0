# SPDX-License-Identifier: Apache-2.0
"""Independently authored conventional text-evidence comparator."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import sys
from typing import Any


def source(document: str, text: str, start: int, end: int) -> dict[str, Any]:
    return {"document": document, "start": start, "end": end, "quote": text[start:end]}


def paragraphs(document: str, text: str) -> list[dict[str, Any]]:
    out = []
    for match in re.finditer(r"[^\n]+", text):
        left = len(match.group()) - len(match.group().lstrip())
        right = len(match.group().rstrip())
        if right > left:
            start, end = match.start() + left, match.start() + right
            value = text[start:end]
            heading = re.match(
                r"(?i)^(?:(?:section|clause|article)\s+)?(\d+(?:\.\d+)*(?:\([a-z]\))?)[.):\s–—-]+", value
            )
            out.append({"section": heading.group(1) if heading else None, "source": source(document, text, start, end)})
    return out


def redline(original: str, revised: str) -> list[dict[str, Any]]:
    a = list(re.finditer(r"\S+", original))
    b = list(re.finditer(r"\S+", revised))
    result = []
    for kind, i, j, k, m in difflib.SequenceMatcher(
        a=[x.group() for x in a], b=[x.group() for x in b], autojunk=False
    ).get_opcodes():
        if kind == "equal":
            continue
        a0 = a[i].start() if i < len(a) else len(original)
        a1 = a[j - 1].end() if j > i else a0
        b0 = b[k].start() if k < len(b) else len(revised)
        b1 = b[m - 1].end() if m > k else b0
        result.append(
            {"kind": kind, "before": source("original", original, a0, a1), "after": source("revised", revised, b0, b1)}
        )
    return result


def exact_changes(original: str, revised: str) -> list[dict[str, Any]]:
    result = []
    for kind, i, j, k, m in difflib.SequenceMatcher(a=original, b=revised, autojunk=False).get_opcodes():
        if kind != "equal":
            result.append(
                {
                    "kind": kind,
                    "original_span": source("original", original, i, j),
                    "revised_span": source("revised", revised, k, m),
                }
            )
    return result


def reference_report(clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for clause in clauses:
        if clause["section"]:
            index.setdefault(clause["section"].casefold(), []).append(clause)
    result = []
    for clause in clauses:
        ref = clause["source"]
        for match in re.finditer(r"(?i)\b(?:section|clause|article)\s+(\d+(?:\.\d+)*(?:\([a-z]\))?)\b", ref["quote"]):
            if match.start() == 0:
                continue
            targets = index.get(match.group(1).casefold(), [])
            result.append(
                {
                    "from": ref,
                    "target": match.group(1),
                    "status": "resolved" if len(targets) == 1 else "missing" if not targets else "ambiguous",
                    "targets": [x["source"] for x in targets],
                }
            )
    return result


def text_evidence(case: dict[str, Any]) -> dict[str, Any]:
    original = case.get("original_text", case.get("original", ""))
    revised = case.get("revised_text", case.get("revised", ""))
    clauses = paragraphs("revised", revised)
    duty = re.compile(
        r"(?i)\b(shall|must|will|undertakes?|agrees?|may\s+(?:only|not)|is\s+(?:required|prohibited)|solely|exclusively)\b"
    )
    obligations = []
    for clause in clauses:
        if duty.search(clause["source"]["quote"]):
            obligations.append(
                {
                    "section": clause["section"],
                    "source": clause["source"],
                    "interpretation": "candidate duty; professional interpretation unassessed",
                }
            )
    return {
        "case_id": case.get("case_id"),
        "arm": "D",
        "method": "independent conventional difflib plus explicit text rules",
        "document_hashes": {
            "original": hashlib.sha256(original.encode()).hexdigest(),
            "revised": hashlib.sha256(revised.encode()).hexdigest(),
        },
        "changes": redline(original, revised),
        "clauses": clauses,
        "obligations": obligations,
        "references": reference_report(clauses),
        "professional_acceptance": "unknown",
    }


FAMILIES = {
    "R1_PURPOSE": r"\bpurpose\b|\buse\b.*\b(?:confidential|information)\b",
    "R2_CONFIDENTIALITY_TERM": r"\bconfidentiality\b|\b(?:keep|maintain|hold|preserve|protect|secrecy|nondisclosure|non-disclosure)\b.*\b(?:confidential|confidence|secret|information)\b|\b(?:confidential|secrecy)\b.*\b(?:duty|duties|obligation|period|years?|months?)\b",
    "R3_RETURN_DEADLINE": r"\b(?:return|destr(?:oy|uction)|delete|erasure|erase|purge)\b",
    "R4_COMPELLED_NOTICE": r"\b(?:compell\w*|subpoena|court order|disclosure.*(?:law|legal)|(?:law|legal).*disclosure)\b",
    "R5_RESIDUALS": r"\b(?:residuals?|unaided memory|remembered information)\b",
    "R6_ASSIGNMENT": r"\b(?:assign\w*|transfer\s+(?:this|the)\s+(?:agreement|contract))\b",
    "R7_GOVERNING_LAW": r"\b(?:governing law|governed|laws of|construed under)\b",
    "R8_REPRESENTATIVES": r"\b(?:representatives|advis[eo]rs?|employees|personnel|affiliates)\b",
}

SMALL = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def number(value: str) -> int | None:
    value = value.casefold().replace("–", "-")
    if value.isdigit():
        return int(value)
    parts = value.replace("-", " ").split()
    if parts and all(x in SMALL for x in parts):
        return sum(SMALL[x] for x in parts)
    return None


def durations(text: str, wanted: str) -> list[int]:
    words = "|".join(SMALL)
    pattern = rf"\b(\d+|(?:{words})(?:[- ](?:{words}))?)\s*(?:\(\d+\)\s*)?(?:(calendar|business|working)\s+)?(days?|months?|years?)\b"
    found = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        value = number(match.group(1))
        unit = match.group(3).casefold()
        if value is not None and (
            (wanted == "months" and unit.startswith(("month", "year"))) or (wanted == "days" and unit.startswith("day"))
        ):
            found.append(value * (12 if unit.startswith("year") else 1))
    return found


def dedupe_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out, seen = [], set()
    for ref in refs:
        identity = (ref["document"], ref["start"], ref["end"])
        if identity not in seen:
            seen.add(identity)
            out.append(ref)
    return out


def effective_clauses(case: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    clauses = paragraphs("revised", case["revised_text"])
    escalations = []
    touched: set[str] = set()
    for amendment in case.get("amendments", []):
        text = amendment["text"]
        document = "amendment:" + amendment["id"]
        full = source(document, text, 0, len(text))
        pattern = r'(?is)\b(?:Section|Clause)\s+(\d+(?:\.\d+)*)\s+is\s+(?:hereby\s+)?replaced(?:\s+in\s+its\s+entirety)?\s+(?:with|by)(?::|\s+the\s+following:)?\s*["“](.*?)["”]'
        matches = list(re.finditer(pattern, text))
        precedence = bool(re.search(r"(?i)\b(prevails?|supersedes?|takes precedence)\b", text))
        if not matches or not precedence:
            escalations.append(
                {
                    "code": "UNSUPPORTED_AMENDMENT",
                    "detail": "Amendment does not provide an unambiguous supported replacement and precedence instruction.",
                    "sources": [full],
                }
            )
            continue
        for match in matches:
            section = match.group(1)
            targets = [x for x in clauses if x["section"] == section]
            if len(targets) != 1 or section in touched:
                escalations.append(
                    {
                        "code": "AMBIGUOUS_AMENDMENT",
                        "detail": "Repeated or non-unique replacement target requires counsel review.",
                        "sources": [full],
                    }
                )
                continue
            touched.add(section)
            ref = source(document, text, match.start(2), match.end(2))
            clauses = [x for x in clauses if x["section"] != section]
            clauses.append({"section": section, "source": ref, "amendment_instruction": full})
    return clauses, escalations


def expand_sources(selected: list[dict[str, Any]], clauses: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    index: dict[str, list[dict[str, Any]]] = {}
    definitions = []
    for clause in clauses:
        if clause["section"]:
            index.setdefault(clause["section"].casefold(), []).append(clause)
        m = re.search(
            r'["“]([^"”]+)["”]\s+(?:means|shall mean|is defined as)\b', clause["source"]["quote"], re.IGNORECASE
        )
        if m:
            definitions.append((m.group(1).casefold(), clause))
    pending = list(selected)
    result: list[dict[str, Any]] = []
    visited = set()
    unresolved = False
    while pending:
        clause = pending.pop()
        ref = clause["source"]
        identity = (ref["document"], ref["start"], ref["end"])
        if identity in visited:
            continue
        visited.add(identity)
        result.append(ref)
        if clause.get("amendment_instruction"):
            result.append(clause["amendment_instruction"])
        text = ref["quote"]
        for m in re.finditer(r"(?i)\b(?:section|clause|article)\s+(\d+(?:\.\d+)*(?:\([a-z]\))?)\b", text):
            if m.start() == 0:
                continue
            targets = index.get(m.group(1).casefold(), [])
            if len(targets) != 1:
                unresolved = True
            else:
                pending.extend(targets)
        for term, definition in definitions:
            if term in text.casefold() and definition is not clause:
                pending.append(definition)
    return dedupe_refs(result), unresolved


def classify(rule: str, texts: list[str], unresolved: bool) -> tuple[str, str]:
    text = "\n".join(texts).casefold()
    if not texts:
        return (
            ("pass", "No residual-use permission is present.")
            if rule == "R5_RESIDUALS"
            else ("absent", "No supported clause was located for this policy.")
        )
    if unresolved:
        return "uncertain", "A material cross-reference could not be resolved uniquely."
    if rule == "R1_PURPOSE":
        if re.search(
            r"\b(?:any|other|all)\s+(?:lawful\s+|business\s+|commercial\s+)?purposes?\b|\bcompet(?:e|itive|ition)\b|\bown\s+(?:business|commercial)\s+purposes?\b",
            text,
        ):
            return "deviation", "The permitted use extends beyond evaluating the business relationship."
        restricted = bool(re.search(r"\b(?:only|solely|exclusively)\b", text)) and not bool(
            re.search(r"\bnot\s+only\b", text)
        )
        purpose = bool(re.search(r"\b(?:evaluat\w*|assess\w*|consider\w*|explor\w*)\b", text)) and bool(
            re.search(r"\b(?:business|commercial|transaction|relationship|collaboration)\b", text)
        )
        return (
            ("pass", "An express exclusive business-evaluation restriction was located.")
            if restricted and purpose
            else ("uncertain", "The complete exclusive use limitation is not mechanically clear.")
        )
    if rule == "R2_CONFIDENTIALITY_TERM":
        if re.search(r"trade[- ]secrets?", text):
            return "uncertain", "Separate trade-secret survival requires counsel interpretation."
        values = set(durations(text, "months"))
        indefinite = bool(re.search(r"indefinite|perpetu|forever|no\s+(?:time\s+)?limit|never\s+expire", text))
        if len(values) > 1 or (values and indefinite):
            return "uncertain", "Multiple or conflicting confidentiality durations were located."
        if indefinite:
            return "deviation", "The general confidentiality duty is indefinite."
        if len(values) != 1:
            return "uncertain", "No unique supported general confidentiality duration was resolved."
        value = next(iter(values))
        return (
            ("pass", f"Explicit general duration is {value} months.")
            if 12 <= value <= 36
            else ("deviation", f"Explicit general duration is {value} months, outside the playbook interval.")
        )
    if rule == "R3_RETURN_DEADLINE":
        if re.search(
            r"business\s+days|working\s+days|reasonable\s+(?:efforts?|endeavou?rs?)|commercially\s+reasonable", text
        ):
            return "uncertain", "Business-day or effort qualification requires review."
        if "request" not in text:
            return "uncertain", "A request trigger is not explicit."
        values = set(durations(text, "days"))
        if len(values) != 1:
            return "uncertain", "No unique supported return/destruction deadline was resolved."
        value = next(iter(values))
        return (
            ("pass", f"Explicit request-triggered deadline is {value} days.")
            if 1 <= value <= 30
            else ("deviation", f"Explicit request-triggered deadline is {value} days, outside the playbook interval.")
        )
    if rule == "R4_COMPELLED_NOTICE":
        if re.search(
            r"without\s+(?:(?:prior|advance|written|any)\s+)*notice|no\s+(?:prior\s+)?notice|notice\s+(?:is\s+)?not\s+required|need\s+not\s+(?:give|provide)\s+notice",
            text,
        ):
            return "deviation", "An express no-notice option was located."
        if "notice" not in text and not re.search(r"\bnotify\b", text):
            return "deviation", "The compelled-disclosure permission does not require notice."
        before = bool(re.search(r"prior|advance|before", text))
        permitted = bool(
            re.search(
                r"legally\s+permitted|permitted\s+by\s+law|law\s+permits|not\s+prohibited\s+by\s+law|legally\s+allowed",
                text,
            )
        )
        return (
            ("pass", "Prior notice subject to legal permission is explicit.")
            if before and permitted
            else ("uncertain", "The complete prior-notice and legal-permission condition is unclear.")
        )
    if rule == "R5_RESIDUALS":
        prohibited = bool(
            re.search(
                r"neither\b.{0,100}\b(?:may|shall)\s+use|(?:may|shall|must|can)\s+not\s+use|no\s+(?:right|permission|licen[cs]e)\s+to\s+use|use\b.{0,40}\b(?:prohibited|forbidden)",
                text,
            )
        )
        if prohibited:
            return "pass", "Express prohibition of residual use was located."
        if re.search(
            r"\b(?:may|can|permitted|allowed|free|entitled)\b.*\buse\b|\buse\b.*\b(?:permitted|allowed)\b", text
        ):
            return "deviation", "Express residual-use permission was located."
        return "uncertain", "Residual-use treatment is unclear."
    if rule == "R6_ASSIGNMENT":
        exception = bool(
            re.search(
                r"\b(?:except|however|provided that|notwithstanding)\b|consent\s+(?:is\s+)?not\s+required|without\s+(?:any\s+)?restriction|freely\s+assign",
                text,
            )
        )
        if exception:
            return "deviation", "Assignment consent has an express exception or is unrestricted."
        complete = "prior" in text and "written" in text and "consent" in text
        prohibited = bool(
            re.search(r"neither|shall\s+not|may\s+not|must\s+not|cannot|no\s+party|requires?|only\s+with", text)
        )
        if complete and prohibited:
            return "pass", "Assignment requires prior written consent."
        if "consent" not in text and re.search(r"\bmay\s+assign|\bassign(?:ment)?\s+is\s+permitted", text):
            return "deviation", "Assignment permission has no consent condition."
        return "uncertain", "The complete prior written consent condition is unclear."
    if rule == "R7_GOVERNING_LAW":
        jurisdictions = re.findall(
            r"(?:laws?\s+(?:of\s+)?(?:the\s+province\s+of\s+)?)(ontario|qu[eé]bec|new york|california|england|british columbia|alberta|canada|delaware|france)",
            text,
        )
        meaningful = set(jurisdictions) - {"canada"}
        if len(meaningful) > 1:
            return "uncertain", "Conflicting governing-law jurisdictions were located."
        if meaningful == {"ontario"}:
            return "pass", "Ontario governing law is explicit."
        if meaningful:
            return "deviation", "An express governing jurisdiction other than Ontario was located."
        return "uncertain", "The governing jurisdiction could not be resolved explicitly."
    if rule == "R8_REPRESENTATIVES":
        if re.search(
            r"not\s+(?:be\s+|remain\s+)?(?:responsible|liable)|no\s+(?:responsibility|liability)|disclaims?\s+(?:responsibility|liability)",
            text,
        ):
            return "deviation", "Recipient responsibility for representatives is expressly excluded."
        need = bool(re.search(r"need[- ]to[- ]know|need\s+to\s+know", text))
        responsible = bool(re.search(r"responsible|liable", text)) and bool(
            re.search(r"breach|violation|acts\s+and\s+omissions", text)
        )
        return (
            ("pass", "Need-to-know and continuing responsibility are explicit.")
            if need and responsible
            else ("uncertain", "Need-to-know or breach responsibility is incomplete.")
        )
    raise ValueError("Unknown rule")


def review(case: dict[str, Any], playbook: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = text_evidence(case)
    docs = {"original": case["original_text"], "revised": case["revised_text"]}
    docs.update({"amendment:" + a["id"]: a["text"] for a in case.get("amendments", [])})
    supported = (
        case.get("jurisdiction") == "Ontario, Canada"
        and case.get("document_family") == "commercial mutual NDA"
        and case.get("playbook_version") == "ONT-NDA-RESEARCH-1.0"
        and case.get("source_class") == "synthetic"
    )
    clauses, escalations = effective_clauses(case)
    if not supported:
        escalations.append(
            {
                "code": "SCOPE_UNSUPPORTED",
                "detail": "This input is outside the declared jurisdiction, family, playbook, or research source scope.",
                "sources": [],
            }
        )
    if re.search(
        r"(?i)enforceab|should\s+(?:we|i)\s+sign|privacy\s+compliance|tax\s+(?:advice|treatment|consequences)|employment|patent\s+ownership|file\s+(?:this|the)\s+(?:case|claim)",
        case.get("request", ""),
    ):
        escalations.append(
            {
                "code": "REQUEST_OUT_OF_SCOPE",
                "detail": "The additional request requires unsupported legal judgment; no substantive answer is provided.",
                "sources": [],
            }
        )
    results: list[dict[str, Any]] = []
    obligations: list[dict[str, Any]] = []
    for rule, pattern in FAMILIES.items():
        selected = [c for c in clauses if re.search(pattern, c["source"]["quote"], re.IGNORECASE)]
        if rule == "R2_CONFIDENTIALITY_TERM":
            selected = [
                c
                for c in selected
                if not re.search(
                    r"(?i)^\s*(?:\d+[.)]\s*)?(?:Return|Compelled|Representatives|Purpose|Residuals|Assignment)\.",
                    c["source"]["quote"],
                )
            ]
        refs, unresolved = expand_sources(selected, clauses)
        status, reason = (
            classify(
                rule,
                [r["quote"] for r in refs if r not in [c.get("amendment_instruction") for c in clauses]],
                unresolved,
            )
            if supported
            else ("out_of_scope", "Input outside supported scope.")
        )
        if supported and any(x["code"] in {"UNSUPPORTED_AMENDMENT", "AMBIGUOUS_AMENDMENT"} for x in escalations):
            status, reason = (
                "uncertain",
                "An unsupported amendment may alter this policy result; no current conclusion is supported.",
            )
        severity = 3 if rule in {"R6_ASSIGNMENT", "R8_REPRESENTATIVES"} else 5
        results.append({"rule_id": rule, "status": status, "severity": severity, "sources": refs, "reason": reason})
        obligations.extend({"family": rule, "source": ref} for ref in refs)
        if status in {"uncertain", "absent", "deviation"}:
            escalations.append({"code": rule, "detail": reason, "sources": refs})
    changes = exact_changes(case["original_text"], case["revised_text"])
    return {
        "case_id": case["case_id"],
        "arm": "D",
        "method": evidence["method"],
        "source_hashes": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in docs.items()},
        "changes": changes,
        "obligations": obligations,
        "rule_results": results,
        "escalations": escalations,
        "proposed_revisions": [],
        "supported_scope": supported,
        "professional_acceptance": "unknown",
    }


if __name__ == "__main__":
    value = json.load(sys.stdin)
    print(json.dumps(review(value), ensure_ascii=False, sort_keys=True))

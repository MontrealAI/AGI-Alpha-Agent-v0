# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import difflib
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCOPE = json.loads((ROOT / "protocol/scope.json").read_text())
RULES = SCOPE["rules"]
WORDS = {
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
NUMBER_PATTERN = r"\d+|(?:" + "|".join(WORDS) + r")(?:[ -](?:one|two|three|four|five|six|seven|eight|nine))?"
FAMILY = {
    "R1_PURPOSE": r"\b(purpose|use|using)\b",
    "R2_CONFIDENTIALITY_TERM": r"\b(confidentiality|confidential|non-disclosure|nondisclosure|protection period)\b",
    "R3_RETURN_DEADLINE": r"\b(return|destroy|destruction|delete|deletion|erase|erasure)\b",
    "R4_COMPELLED_NOTICE": r"\b(compelled|compulsory|subpoena|court order|legally required|legal process)\b",
    "R5_RESIDUALS": r"\b(residuals?|unaided memory|unaided recollection)\b",
    "R6_ASSIGNMENT": r"\b(assign|assignment|transfer this agreement)\b",
    "R7_GOVERNING_LAW": r"\b(governed|governing law|laws of|construed)\b",
    "R8_REPRESENTATIVES": r"\b(representatives?|employees|advisers|advisors|personnel)\b",
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def validate_input(case: dict[str, Any]) -> None:
    expected = set(SCOPE["input_schema"])
    if not isinstance(case, dict) or set(case) != expected:
        raise ValueError("INPUT_SCHEMA")
    for key in expected - {"amendments"}:
        if not isinstance(case[key], str) or not case[key].strip():
            raise ValueError("MISSING_TEXT:" + key)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", case["case_id"]):
        raise ValueError("CASE_ID")
    if case["source_class"] != "synthetic":
        raise ValueError("RESEARCH_SYNTHETIC_INPUT_REQUIRED")
    if len(case["original_text"]) > 30000 or len(case["revised_text"]) > 30000:
        raise ValueError("INPUT_BUDGET")
    if not isinstance(case["amendments"], list) or len(case["amendments"]) > 4:
        raise ValueError("AMENDMENT_BUDGET")
    seen = set()
    for item in case["amendments"]:
        if not isinstance(item, dict) or set(item) != {"id", "text"}:
            raise ValueError("AMENDMENT_SCHEMA")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", item["id"]) or item["id"] in seen:
            raise ValueError("AMENDMENT_ID")
        seen.add(item["id"])
        if not isinstance(item["text"], str) or not item["text"] or len(item["text"]) > 8000:
            raise ValueError("AMENDMENT_TEXT")


def documents(case: dict[str, Any]) -> dict[str, str]:
    return {
        "original": case["original_text"],
        "revised": case["revised_text"],
        **{"amendment:" + item["id"]: item["text"] for item in case["amendments"]},
    }


def span(document: str, text: str, start: int, end: int) -> dict[str, Any]:
    return {"document": document, "start": start, "end": end, "quote": text[start:end]}


def blocks(text: str, document: str) -> list[dict[str, Any]]:
    found = []
    for match in re.finditer(r"[^\r\n]+", text):
        raw = match.group()
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right <= left:
            continue
        source = span(document, text, match.start() + left, match.start() + right)
        numbered = re.match(
            r"(?:Section\s+|Clause\s+|Article\s+)?(\d+(?:\.\d+)*(?:\([a-z]\))?)[.)\s]", source["quote"], re.IGNORECASE
        )
        found.append({"id": numbered.group(1).rstrip(".") if numbered else "", "source": source})
    return found


def number(text: str) -> int:
    if text.isdigit():
        return int(text)
    return sum(WORDS.get(word, 0) for word in re.split(r"[ -]", text.lower()))


def durations(text: str, target: str) -> list[int]:
    out = []
    unit = r"months?|years?" if target == "months" else r"days?"
    for match in re.finditer(
        r"\b(" + NUMBER_PATTERN + r")\s*(?:\(\d+\)\s*)?(?:calendar\s+|business\s+)?(" + unit + r")\b", text.lower()
    ):
        value = number(match.group(1))
        if target == "months" and match.group(2).startswith("year"):
            value *= 12
        out.append(value)
    return sorted(set(out))


def relevant(rule_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [row for row in rows if re.search(FAMILY[rule_id], row["source"]["quote"], re.IGNORECASE)]
    if rule_id == "R1_PURPOSE":
        selected = [
            row
            for row in selected
            if not re.search(r"\b(residual|unaided memory)\b", row["source"]["quote"], re.IGNORECASE)
        ]
    if rule_id == "R2_CONFIDENTIALITY_TERM":
        selected = [
            row
            for row in selected
            if re.search(
                r"confidentiality|non.?disclosure|(?:keep|maintain|remain|treat|hold).*confidential|protection period|confidential.*duty",
                row["source"]["quote"],
                re.IGNORECASE,
            )
            and re.search(
                r"\b(for |period|duration|months?|years?|indefinite|perpetu|continue|surviv|term)\b",
                row["source"]["quote"],
                re.IGNORECASE,
            )
        ]
    return selected


def decide(rule_id: str, text: str, present: bool) -> tuple[str, str]:
    t = text.lower().replace("’", "'")
    if not present:
        if rule_id == "R5_RESIDUALS":
            return (
                "pass",
                "No express residual-use permission was found; this policy does not require a residuals clause.",
            )
        return "absent", "No supported passage for this required playbook item was identified."
    if rule_id == "R1_PURPOSE":
        if re.search(
            r"any (lawful |business )?purpose|competitive use|competing products|including competition|without restriction",
            t,
        ):
            return "deviation", "The passage permits use broader than the declared evaluation purpose."
        if (
            re.search(r"\b(only|solely|exclusively)\b", t)
            and re.search(r"\b(evaluat\w*|assess\w*)\b", t)
            and re.search(r"business|relationship|transaction|opportunity|collaboration", t)
        ):
            return "pass", "Express exclusive evaluation-use wording was located."
        return "uncertain", "Purpose restriction requires interpretation or a missing definition."
    if rule_id == "R2_CONFIDENTIALITY_TERM":
        if "trade secret" in t:
            return "uncertain", "Trade-secret survival requires separate professional assessment."
        if re.search(r"indefinit|in perpetuity|perpetual|forever", t):
            return "deviation", "An indefinite general confidentiality duty exceeds this research playbook."
        values = durations(t, "months")
        if len(values) != 1:
            return "uncertain", "The general confidentiality duration is missing, conflicting or not resolvable."
        return (
            "pass" if 12 <= values[0] <= 36 else "deviation"
        ), f"Explicit general duration: {values[0]} months; policy range 12-36."
    if rule_id == "R3_RETURN_DEADLINE":
        if re.search(
            r"business days|reasonable (efforts|endeavou?rs)|as (soon as|reasonably) practicable|commercially reasonable",
            t,
        ):
            return "uncertain", "The deadline has a business-day or effort qualifier outside the mechanical policy."
        if not re.search(r"request|demand", t):
            return "uncertain", "The deadline is not expressly linked to a request."
        values = durations(t, "days")
        if len(values) != 1:
            return "uncertain", "The return deadline is missing, conflicting or not resolvable."
        return (
            "pass" if 1 <= values[0] <= 30 else "deviation"
        ), f"Explicit return period: {values[0]} days; policy range 1-30 calendar days."
    if rule_id == "R4_COMPELLED_NOTICE":
        if re.search(
            r"without (prior )?notice|no (prior )?notice|need not (give|provide|notify)|may (give|provide) notice", t
        ):
            return "deviation", "Prior notice is expressly waived or discretionary."
        has_prior = bool(re.search(r"prior|before|advance", t))
        has_notice = bool(re.search(r"notice|notif", t))
        legal = bool(
            re.search(
                r"legally permitted|permitted by law|law (allows|permits)|lawfully|unless .*prohibit|not prohibited by law",
                t,
            )
        )
        required = bool(re.search(r"\b(must|shall|will)\b", t))
        if has_prior and has_notice and legal and required:
            return "pass", "Required prior notice with an express legal-permission condition was located."
        if not has_notice:
            return "deviation", "Compelled disclosure is addressed without a notice requirement."
        return "uncertain", "Prior notice timing, obligation or legal-permission condition is unclear."
    if rule_id == "R5_RESIDUALS":
        prohibited = bool(
            re.search(
                r"(shall|must|may|will) not (use|exploit)|neither .*may use|no (right|licen[cs]e).*residual|prohibited",
                t,
            )
        )
        permission_text = re.sub(r"neither [^.\n]*?may use", "", t)
        permitted = bool(
            re.search(
                r"\bmay (freely )?(use|exploit)|free to (use|exploit)|permitted to use|right to use", permission_text
            )
        )
        if prohibited and permitted:
            return "uncertain", "Residual-use wording contains potentially conflicting permissions and prohibitions."
        if prohibited:
            return "pass", "Express residual-use prohibition was located."
        if permitted:
            return "deviation", "Residual-use permission departs from the playbook."
        return "uncertain", "Residual-use effect is unclear."
    if rule_id == "R6_ASSIGNMENT":
        if re.search(r"without (the .*?)?consent|without .*written consent", t) and not re.search(
            r"(may|shall|must|will) not assign|neither .*may assign|no .*may assign", t
        ):
            return "deviation", "Assignment without consent appears expressly permitted."
        if re.search(r"except|other than|affiliate|successor|not unreasonably withheld", t):
            return "deviation", "An assignment consent exception or qualification requires counsel review."
        if re.search(r"prior written consent", t) and re.search(
            r"(may|shall|must|will) not assign|neither .*may assign|requires?|subject to|only with", t
        ):
            return "pass", "Prior written consent restriction was located."
        return "uncertain", "Assignment consent requirement is incomplete or unclear."
    if rule_id == "R7_GOVERNING_LAW":
        laws = re.findall(
            r"(?:laws? of|governed by)\s+(?:the\s+)?(?:province of\s+|state of\s+)?([a-z ]+?)(?:[,.;\n]|$)", t
        )
        ontario = "ontario" in t
        foreign = any(
            any(word in law for word in ("quebec", "delaware", "new york", "england", "california", "alberta"))
            for law in laws
        )
        if ontario and foreign:
            return "uncertain", "Potentially conflicting governing-law passages were located."
        if ontario:
            return "pass", "Express Ontario governing-law wording was located; enforceability is not assessed."
        return "deviation", "The governing-law passage does not state Ontario."
    if rule_id == "R8_REPRESENTATIVES":
        if re.search(r"not (responsible|liable)|no (responsibility|liability)|not be (responsible|liable)", t):
            return "deviation", "The recipient expressly disclaims responsibility for representatives."
        need = bool(re.search(r"need[ -]to[ -]know|need to know", t))
        liable = bool(re.search(r"responsible|liable|accountable", t))
        if need and liable and re.search(r"breach|violat|compliance|acts and omissions", t):
            return "pass", "Need-to-know limitation and responsibility wording were located."
        return "uncertain", "Need-to-know or responsibility wording requires further review."
    raise ValueError("UNKNOWN_RULE")


def exact_changes(case: dict[str, Any]) -> list[dict[str, Any]]:
    old, new = case["original_text"], case["revised_text"]
    changes: list[dict[str, Any]] = []
    for tag, a, b, c, d in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag != "equal":
            changes.append(
                {
                    "kind": tag,
                    "original_span": span("original", old, a, b) if a != b else None,
                    "revised_span": span("revised", new, c, d) if c != d else None,
                }
            )
    for item in case["amendments"]:
        changes.append(
            {
                "kind": "amendment",
                "original_span": None,
                "revised_span": span("amendment:" + item["id"], item["text"], 0, len(item["text"])),
            }
        )
    return changes


def packet(case: dict[str, Any], stage: str = "B") -> dict[str, Any]:
    validate_input(case)
    if stage not in {"B", "C1", "C"}:
        raise ValueError("UNKNOWN_STAGE")
    docs = documents(case)
    supported = (
        case["jurisdiction"] == SCOPE["jurisdiction"]
        and case["document_family"] == SCOPE["document_family"]
        and case["playbook_version"] == SCOPE["playbook_version"]
    )
    rows = blocks(case["revised_text"], "revised")
    escalations: list[dict[str, Any]] = []
    superseded: list[dict[str, Any]] = []
    amendments_unresolved = bool(case["amendments"])
    if stage == "C":
        from amendments import apply_explicit_amendments

        rows, superseded, amendment_issues = apply_explicit_amendments(case, rows)
        escalations.extend(amendment_issues)
        amendments_unresolved = bool(amendment_issues)
    if amendments_unresolved:
        escalations.append(
            {
                "code": "AMENDMENT_REVIEW",
                "detail": "One or more amendments require professional resolution before reliance.",
                "sources": [span(k, v, 0, len(v)) for k, v in docs.items() if k.startswith("amendment:")],
            }
        )
    if re.search(
        r"enforceab|legal advice|tax|privacy|employment|patent|securities|should (we|i) sign|negotiate|file (this|a)",
        case["request"],
        re.IGNORECASE,
    ):
        escalations.append(
            {
                "code": "REQUEST_OUT_OF_SCOPE",
                "detail": "Excluded legal questions are not answered; this packet only addresses mechanical NDA support.",
                "sources": [],
            }
        )
    obligations = []
    rules = []
    for rule in RULES:
        rid = rule["id"]
        selected = relevant(rid, rows)
        for row in selected:
            obligations.append({"family": rid, "source": row["source"]})
        context = selected
        unresolved: list[str] = []
        if stage in {"C1", "C"} and selected:
            from references import resolve_context

            context, unresolved = resolve_context(selected, rows)
        text = "\n".join(item["source"]["quote"] for item in context)
        status, reason = (
            decide(rid, text, bool(selected))
            if supported
            else ("out_of_scope", "Jurisdiction, family or playbook version is unsupported.")
        )
        if supported and unresolved:
            status, reason = "uncertain", "An explicit reference could not be resolved safely."
        if supported and amendments_unresolved:
            status, reason = "uncertain", "Unresolved amendment precedence prevents a current consolidated conclusion."
        if (
            supported
            and stage == "B"
            and selected
            and re.search(
                r"\b(section|clause|article)\s+\d|\b(?:Protection|Return|Review|Confidentiality) Period\b",
                text,
                re.IGNORECASE,
            )
        ):
            status, reason = "uncertain", "Reference-dependent wording requires the retained resolver or manual review."
        sources = [item["source"] for item in context]
        for change in superseded:
            if change["replacement_source"] in sources and change["authority_source"] not in sources:
                sources.append(change["authority_source"])
        rules.append(
            {"rule_id": rid, "status": status, "severity": rule["severity"], "sources": sources, "reason": reason}
        )
        if status in {"deviation", "uncertain", "absent", "out_of_scope"}:
            escalations.append({"code": rid, "detail": reason, "sources": sources})
        for value in unresolved:
            escalations.append({"code": "UNRESOLVED_REFERENCE", "detail": value, "sources": sources})
    if not supported:
        escalations.append(
            {
                "code": "SCOPE_UNSUPPORTED",
                "detail": "No legal or mechanical playbook conclusion is supported for the requested scope.",
                "sources": [],
            }
        )
    return {
        "schema": "legal-support-packet/v1",
        "case_id": case["case_id"],
        "implementation_stage": stage,
        "playbook_version": case["playbook_version"],
        "source_hashes": {k: sha(v) for k, v in docs.items()},
        "changes": exact_changes(case),
        "obligations": obligations,
        "rule_results": rules,
        "escalations": escalations,
        "proposed_revisions": [],
        "superseded_passages": superseded,
        "supported_scope": supported,
        "professional_acceptance": "unknown",
        "legal_correctness": "NOT_ASSESSED",
        "decision": "COUNSEL_REVIEW_REQUIRED",
        "scope": SCOPE["offering"],
        "limitations": [
            "Original synthetic research documents; not real client work.",
            "A mechanical policy match is not a conclusion about legal sufficiency or enforceability.",
            "Every packet requires independent qualified professional review before legal reliance.",
            "No automatic legal revision, negotiation, filing, signature or settlement.",
        ],
    }


def check_packet(case: dict[str, Any], result: dict[str, Any]) -> list[str]:
    docs = documents(case)
    errors = []
    if result["source_hashes"] != {k: sha(v) for k, v in docs.items()}:
        errors.append("SOURCE_HASH_MISMATCH")

    def inspect(value: Any) -> None:
        if isinstance(value, dict):
            if {"document", "start", "end", "quote"} <= set(value):
                text = docs.get(value["document"])
                if (
                    text is None
                    or type(value["start"]) is not int
                    or type(value["end"]) is not int
                    or not 0 <= value["start"] <= value["end"] <= len(text)
                    or text[value["start"] : value["end"]] != value["quote"]
                ):
                    errors.append("SOURCE_SPAN_MISMATCH")
            for item in value.values():
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)

    inspect(result)
    if result.get("professional_acceptance") != "unknown" or result.get("decision") != "COUNSEL_REVIEW_REQUIRED":
        errors.append("PROFESSIONAL_BOUNDARY")
    if result.get("proposed_revisions"):
        errors.append("UNSUPPORTED_REVISION")
    if len(result["rule_results"]) != len(RULES) or {row["rule_id"] for row in result["rule_results"]} != {
        row["id"] for row in RULES
    }:
        errors.append("RULE_COMPLETENESS")
    return sorted(set(errors))


def render_html(case: dict[str, Any], result: dict[str, Any]) -> str:
    esc = html.escape
    rows = "".join(
        f"<tr><td>{esc(r['rule_id'])}</td><td>{esc(r['status'])}</td><td>{esc(r['reason'])}</td><td>"
        + "".join(
            f"<blockquote>{esc(s['quote'])}<small>{esc(s['document'])} [{s['start']}:{s['end']}]</small></blockquote>"
            for s in r["sources"]
        )
        + "</td></tr>"
        for r in result["rule_results"]
    )
    sources = "".join(f"<h3>{esc(name)}</h3><pre>{esc(text)}</pre>" for name, text in documents(case).items())
    issues = "".join(f"<li>{esc(e['code'])}: {esc(e['detail'])}</li>" for e in result["escalations"])
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"
        + esc(case["case_id"])
        + " - NDA review support</title><style>body{font:16px/1.55 system-ui;margin:3rem auto;padding:0 1.4rem;max-width:1100px;color:#182338}h1,h2{color:#4c237c}table{border-collapse:collapse;width:100%}td,th{border:1px solid #cbd1df;padding:.7rem;text-align:left;vertical-align:top}blockquote{margin:0 0 1rem;padding:.7rem;background:#f4f1fa}small{display:block;color:#566}pre{white-space:pre-wrap;background:#f3f5f9;padding:1rem}.notice{padding:1rem;background:#fff3d6;border-left:4px solid #a86600}</style><h1>"
        + esc(case["case_id"])
        + " · NDA change-control packet</h1><p class='notice'><strong>COUNSEL REVIEW REQUIRED / EXAMEN JURIDIQUE REQUIS.</strong> Synthetic research document. Mechanical playbook checks only; professional legal correctness is unassessed. Document de recherche synthétique; aucune validation juridique professionnelle.</p><p>Playbook: "
        + esc(case["playbook_version"])
        + ". Source offsets use Unicode code points.</p><h2>Source-linked checks</h2><table><thead><tr><th>Rule</th><th>Result</th><th>Reason</th><th>Evidence</th></tr></thead><tbody>"
        + rows
        + "</tbody></table><h2>Questions and escalation</h2><ul>"
        + issues
        + "</ul><h2>Original source documents</h2>"
        + sources
        + "</html>"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["B", "C1", "C"], default="B")
    parser.add_argument("--input")
    args = parser.parse_args()
    case = json.loads(Path(args.input).read_text() if args.input else sys.stdin.read())
    result = packet(case, args.stage)
    errors = check_packet(case, result)
    if errors:
        raise ValueError(";".join(errors))
    print(json.dumps({"packet": result, "html": render_html(case, result)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

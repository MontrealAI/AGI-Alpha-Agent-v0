# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import difflib
import hashlib
import html
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def produce(case: dict[str, Any], method: str = "characters") -> dict[str, Any]:
    if not isinstance(case.get("case_id"), str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,63}", case["case_id"]):
        raise ValueError("CASE_ID")
    if case.get("source_class") != "synthetic":
        raise ValueError("SYNTHETIC_RESEARCH_INPUT_ONLY")
    old, new = case["original_text"], case["revised_text"]
    if not isinstance(old, str) or not isinstance(new, str) or max(len(old), len(new)) > 30000:
        raise ValueError("TEXT_BUDGET")
    if len(case["amendments"]) > 4:
        raise ValueError("AMENDMENT_BUDGET")
    if method not in {"characters", "lines"}:
        raise ValueError("METHOD")
    a = list(old) if method == "characters" else old.splitlines(keepends=True)
    b = list(new) if method == "characters" else new.splitlines(keepends=True)
    a_offsets, b_offsets = [0], [0]
    for value in a:
        a_offsets.append(a_offsets[-1] + len(value))
    for value in b:
        b_offsets.append(b_offsets[-1] + len(value))
    operations = []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        operations.append(
            {
                "kind": tag,
                "original_span": {
                    "document": "original",
                    "start": a_offsets[i],
                    "end": a_offsets[j],
                    "quote": old[a_offsets[i] : a_offsets[j]],
                },
                "revised_span": {
                    "document": "revised",
                    "start": b_offsets[k],
                    "end": b_offsets[l],
                    "quote": new[b_offsets[k] : b_offsets[l]],
                },
            }
        )
    docs = {"original": old, "revised": new}
    for item in case["amendments"]:
        if not isinstance(item.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", item["id"]):
            raise ValueError("AMENDMENT_ID")
        key = "amendment:" + item["id"]
        if key in docs or not isinstance(item["text"], str) or len(item["text"]) > 8000:
            raise ValueError("AMENDMENT_INPUT")
        docs[key] = item["text"]
    return {
        "schema": "legal-reconciliation/v1",
        "case_id": case["case_id"],
        "method": method,
        "source_hashes": {key: hash_text(value) for key, value in docs.items()},
        "documents": docs,
        "operations": operations,
        "amendments": [
            {"document": key, "quote": value, "effect": "NOT_INTERPRETED"}
            for key, value in docs.items()
            if key.startswith("amendment:")
        ],
        "decision": "TEXT_RECONCILIATION_ONLY",
        "professional_acceptance": "unknown",
        "legal_or_playbook_conclusions": [],
        "proposed_revisions": [],
        "review_queue": [
            "Examine every changed passage in its full document context.",
            "Examine each amendment separately; no precedence, validity or consolidated legal effect is inferred.",
            "Use qualified professional judgment for meaning, duties, playbook compliance, risk and the final decision.",
        ],
        "limits": [
            "Original synthetic plain-text research documents only; Office tracked changes, OCR and binary layout are not supported.",
            "Exact text conservation is not semantic equivalence or professional contract acceptance.",
            "No legal advice, automatic edits, negotiation, filing, execution or settlement.",
        ],
    }


def verify(result: dict[str, Any]) -> list[str]:
    errors = []
    docs = result["documents"]
    if result["source_hashes"] != {key: hash_text(value) for key, value in docs.items()}:
        errors.append("HASH")
    ends = {"original": 0, "revised": 0}
    rebuilt = {"original": "", "revised": ""}
    for op in result["operations"]:
        if op["kind"] not in {"equal", "replace", "delete", "insert"}:
            errors.append("KIND")
        for document, previous_end in ends.items():
            source = op[document + "_span"]
            if (
                source["document"] != document
                or type(source["start"]) is not int
                or type(source["end"]) is not int
                or source["start"] != previous_end
                or not source["start"] <= source["end"] <= len(docs[document])
                or docs[document][source["start"] : source["end"]] != source["quote"]
            ):
                errors.append("SPAN")
            ends[document] = source["end"]
            rebuilt[document] += source["quote"]
        before, after = op["original_span"]["quote"], op["revised_span"]["quote"]
        if op["kind"] == "equal" and (before != after or not before):
            errors.append("FALSE_EQUAL")
        if op["kind"] == "insert" and (before or not after):
            errors.append("FALSE_INSERT")
        if op["kind"] == "delete" and (after or not before):
            errors.append("FALSE_DELETE")
        if op["kind"] == "replace" and (not before or not after or before == after):
            errors.append("FALSE_REPLACE")
    if any(rebuilt[name] != docs[name] for name in ends):
        errors.append("RECONSTRUCTION")
    expected = {key for key in docs if key.startswith("amendment:")}
    if {item["document"] for item in result["amendments"]} != expected or len(result["amendments"]) != len(expected):
        errors.append("AMENDMENT_INVENTORY")
    if any(
        item["quote"] != docs.get(item["document"]) or item["effect"] != "NOT_INTERPRETED"
        for item in result["amendments"]
    ):
        errors.append("AMENDMENT_PRESERVATION")
    if (
        result["schema"] != "legal-reconciliation/v1"
        or result["decision"] != "TEXT_RECONCILIATION_ONLY"
        or result["professional_acceptance"] != "unknown"
        or result["legal_or_playbook_conclusions"]
        or result["proposed_revisions"]
    ):
        errors.append("SCOPE")
    return sorted(set(errors))


def render(result: dict[str, Any]) -> str:
    e = html.escape
    redline = []
    for op in result["operations"]:
        before, after = op["original_span"]["quote"], op["revised_span"]["quote"]
        redline.append(
            e(before)
            if op["kind"] == "equal"
            else ("<del>" + e(before) + "</del>" if before else "") + ("<ins>" + e(after) + "</ins>" if after else "")
        )
    documents = "".join(
        "<h2>" + e(name) + "</h2><pre>" + e(text) + "</pre><small>SHA-256 " + result["source_hashes"][name] + "</small>"
        for name, text in result["documents"].items()
    )
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>"
        + e(result["case_id"])
        + " · Source change-control</title><style>body{font:16px/1.6 system-ui;max-width:980px;margin:3rem auto;padding:0 1.5rem;color:#192033}h1,h2{color:#4c227d}pre{white-space:pre-wrap;padding:1.2rem;background:#f5f3fa;border-radius:12px}del{background:#ffe4e9;text-decoration:line-through}ins{background:#dcf6e5;text-decoration:underline}small{overflow-wrap:anywhere}.notice{background:#fff3d9;padding:1rem;border-left:4px solid #ab6c00}</style><h1>"
        + e(result["case_id"])
        + " · Change-control packet / Dossier de modifications</h1><p class='notice'>Text reconciliation only. No legal or playbook conclusion. Counsel review required.<br>Comparaison textuelle uniquement. Aucune conclusion juridique. Examen par un juriste requis.</p><h2>Exact redline / Modifications exactes</h2><pre>"
        + "".join(redline)
        + "</pre><h2>Review queue / Points à examiner</h2><ul>"
        + "".join("<li>" + e(x) + "</li>" for x in result["review_queue"])
        + "</ul>"
        + documents
        + "</html>"
    )


def main() -> None:
    destination = ROOT / sys.argv[1]
    if destination.exists():
        raise ValueError("REFUSE_OVERWRITE")
    destination.mkdir(parents=True)
    records, manifest = [], []
    for case_file in sorted((ROOT / "inputs/reconciliation").glob("*.json")):
        case = json.loads(case_file.read_text())
        for method in ["characters", "lines"]:
            start, cpu = time.perf_counter(), time.process_time()
            result = produce(case, method)
            errors = verify(result)
            if errors:
                raise ValueError(str(errors))
            target = destination / case["case_id"] / method
            target.mkdir(parents=True)
            text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            (target / "packet.json").write_text(text)
            (target / "packet.html").write_text(render(result))
            records.append(
                {
                    "case_id": case["case_id"],
                    "method": method,
                    "seconds": time.perf_counter() - start,
                    "cpu_seconds": time.process_time() - cpu,
                    "packet_sha256": hash_text(text),
                    "accepted_independent": None,
                    "professional_acceptance": "unknown",
                    "measured_review_minutes": None,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "output": str(target.relative_to(ROOT)),
                }
            )
            manifest.append(
                {
                    "input": str((target / "packet.json").relative_to(ROOT)),
                    "output": str((target / "workbench.json").relative_to(ROOT)),
                }
            )
    (destination / "records.json").write_text(json.dumps(records, indent=2) + "\n")
    (destination / "packaging-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"records": len(records), "output": str(destination)}))


if __name__ == "__main__":
    main()

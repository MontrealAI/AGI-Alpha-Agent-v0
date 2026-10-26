import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "inherited/assets"
sys.path.insert(0, str(ASSETS))
from legal_packet import packet
from scorer import all_refs, changed_coverage, document_map, ref_valid

records = []
for path in sorted((ASSETS / "development").glob("*.json")):
    case = json.loads(path.read_text())
    for stage in ("C1", "C"):
        result = packet(case, stage)
        references = all_refs(result)
        missing, changed = changed_coverage(case, result)
        invalid = sum(not ref_valid(ref, document_map(case)) for ref in references)
        if invalid or missing or result["professional_acceptance"] != "unknown":
            raise RuntimeError("DEVELOPMENT_SOURCE_FIDELITY_REFUSED")
        records.append({"case_id": case["case_id"], "stage": stage, "source_refs": len(references),
            "invalid_source_refs": invalid, "changed_characters": changed, "uncovered_changed_characters": missing,
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "professional_acceptance": "unknown"})
report = {"schema": "legal-graph-development-source-fidelity/v1", "records": records,
    "decision": "PASS_EXACT_SOURCE_AND_COMPOSITION_ONLY", "legal_statuses_scored": False,
    "independent_checker": "Frozen evaluator source-span and changed-coverage functions; no answer keys accessed",
    "scope": "Six fixed synthetic development cases; exact sources and composition only, no professional correctness or fresh generalization"}
(ASSETS / "development-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"source_fidelity_checks": len(records), "legal_acceptance": "NOT_ASSESSED"}))

# SPDX-License-Identifier: Apache-2.0
"""Frozen source/complete-handoff acceptance, independent of the arm builders."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re

from evaluate_inventory import evaluate as evaluate_inventory

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def key(row):
    return row.get("line"), row.get("column"), row.get("callee")


def url(source, line=None):
    return f"https://github.com/{source['repository']}/blob/{source['commit']}/{source['path']}" + (f"#L{line}" if line else "")


def project_a(raw, proposal):
    if proposal.get("schema") != "alpha-upgrade-call-request/v1" or proposal.get("sources") != raw["sources"] or proposal.get("id") != raw["id"]:
        raise ValueError("A native request/source identity mismatch")
    return {"schema": "alpha-transfer-extraction/v1", "inputSha256": digest(raw),
            "claims": [{**{field: row[field] for field in ["line", "column", "callee", "before", "after"]},
                        "explanation": row["mapping"]["explanation"]} for row in proposal["calls"]],
            "unresolved": [], "provenance": {"mode": "lossless-audit-projection"}}


def evaluate(raw, oracle, proposal, files, pack, inspection, expected_source_hash, arm):
    """files maps exact delivery-relative filenames to UTF-8 text; no source code runs."""
    errors = []
    response = project_a(raw, proposal) if arm == "A" else proposal
    structural = evaluate_inventory(raw, oracle, response)
    errors.extend(structural["material_errors"])

    def fail(kind, **details):
        errors.append({"kind": kind, **details})

    def payload(name):
        if name not in files:
            fail("MISSING_ARTIFACT", file=name)
            return {}
        try:
            return json.loads(files[name])
        except (ValueError, TypeError):
            fail("INVALID_JSON_ARTIFACT", file=name)
            return {}

    result, receipt, costs = payload("result.json"), payload("receipt.json"), payload("costs.json")
    inventory = payload("call-inventory.json")
    saved_raw, decision = payload("raw-task.json"), payload("decision-record.json")
    if saved_raw != raw:
        fail("RAW_TASK_ARTIFACT_MISMATCH")
    if result.get("inputSha256") != digest(raw):
        fail("RESULT_INPUT_IDENTITY")
    if result.get("productionApproved") is not False or result.get("actualCollectionsUsd") != 0:
        fail("UNSUPPORTED_APPROVAL_OR_COLLECTIONS")
    if result.get("nextAction") not in ["HOLD_UPDATE_AND_TEST", "REVIEW_UNRESOLVED_SCOPE", "RUN_BEHAVIOR_AND_SECURITY_CHECKS"]:
        fail("UNSUPPORTED_NEXT_ACTION")
    if result.get("arm") != arm:
        fail("ARM_IDENTITY")
    result_sha = hashlib.sha256(files.get("result.json", "").encode()).hexdigest()
    if receipt.get("resultSha256") != result_sha:
        fail("RECEIPT_RESULT_IDENTITY")
    if receipt.get("inputSha256") != digest(raw):
        fail("RECEIPT_INPUT_IDENTITY")
    request = result.get("request")
    core = result.get("coreRecord")
    if request is not None and request.get("sources") != raw["sources"]:
        fail("COMPILED_SOURCE_MUTATION")
    if core and decision != core:
        fail("DECISION_RECORD_MISMATCH")
    if not core and decision.get("available") is not False:
        fail("UNRESOLVED_DECISION_RECORD")
    resources = result.get("resources", {})
    for field in ["wallNs", "cpuNs"]:
        if not isinstance(resources.get(field), int) or resources[field] < 0:
            fail("MISSING_MEASURED_RESOURCE", field=field)
    if resources.get("completeDeliveryMoneyUsd", "absent") is not None:
        fail("UNSUPPORTED_COMPLETE_MONEY")
    if not costs.get("unknowns") or costs.get("completeCostsIdentified") is not False or costs.get("noWageConversion") is not True:
        fail("COST_UNKNOWNS_OR_WAGE_CONVERSION")
    for field in ["marginalUsd", "recurringUsd", "fullyLoadedUsd"]:
        if costs.get(field, "absent") is not None:
            fail("UNSUPPORTED_COST_VALUE", field=field)
    if costs.get("actualCollectionsUsd") != 0:
        fail("UNSUPPORTED_COST_COLLECTIONS")

    consumer = raw["sources"][raw["consumer"]["source"]]
    tree = ast.parse(consumer["text"])
    nodes = {(n.lineno, n.col_offset, ast.unparse(n.func)): n for n in ast.walk(tree) if isinstance(n, ast.Call)}
    expected = {key(row): row for row in oracle["calls"]}
    claimed = {key(row): row for row in response.get("claims", [])}
    refusal = {key(row): row for row in response.get("unresolved", [])}
    assessed = {row["id"]: row for row in (core or {}).get("calls", [])}
    core_by_call = {key(row): assessed.get(row["id"]) for row in (request or {}).get("calls", [])}
    if not isinstance(inventory, list):
        fail("INVALID_CALL_INVENTORY")
        inventory = []
    seen, outcomes = set(), {"BINDING_PRESERVED": 0, "BINDING_CONFLICT": 0, "UNRESOLVED": 0}
    for row in inventory:
        call = key(row)
        if call in seen:
            fail("DUPLICATE_HANDOFF_CALL", call=list(call))
            continue
        seen.add(call)
        truth = expected.get(call)
        if truth is None:
            fail("SPURIOUS_HANDOFF_CALL", call=list(call))
            continue
        target_status = truth["expected_core_scope_outcome"] if call in claimed else "UNRESOLVED"
        if row.get("status") != target_status:
            fail("HANDOFF_STATUS_DISAGREEMENT", call=list(call), expected=target_status, actual=row.get("status"))
        else:
            outcomes[target_status] += 1
        exact_snippet = ast.get_source_segment(consumer["text"], nodes[call])
        if row.get("snippet") != exact_snippet:
            fail("CALL_SNIPPET_MISMATCH", call=list(call))
        if row.get("consumerSha256") != consumer["sha256"] or row.get("consumerUrl") != url(consumer, call[0]):
            fail("CALL_SOURCE_EVIDENCE_MISMATCH", call=list(call))
        if call in claimed:
            core_row = core_by_call.get(call)
            if not core_row or core_row.get("status") != target_status:
                fail("CORE_STATUS_DISAGREEMENT", call=list(call))
            elif target_status != "UNRESOLVED":
                for side in ["before", "after"]:
                    if core_row.get(side + "Accepts") != truth["independent_argument_acceptance"][side]:
                        fail("CORE_BINDING_DISAGREEMENT", call=list(call), side=side)
            for side in ["before", "after"]:
                target = row.get("targets", {}).get(side, {})
                expected_target = truth["targets"][side]
                source = raw["sources"][expected_target["source"]]
                if (target.get("source") != expected_target["source"] or target.get("symbol") != expected_target["symbol"]
                    or target.get("sha256") != source["sha256"] or target.get("url") != url(source)):
                    fail("HANDOFF_TARGET_EVIDENCE", call=list(call), side=side)
        elif call not in refusal:
            fail("HANDOFF_WITHOUT_PROPOSAL_CALL", call=list(call))
        if row.get("mappingVerified") is True:
            fail("UNPROVED_RUNTIME_MAPPING", call=list(call))
        if target_status == "UNRESOLVED" and not (row.get("reason") or row.get("qualification")):
            fail("MISSING_UNRESOLVED_REASON", call=list(call))
    for call in expected.keys() - seen:
        fail("OMITTED_HANDOFF_CALL", call=list(call))
    if result.get("handoff", {}).get("inventorySha256") != digest(inventory):
        fail("HANDOFF_INVENTORY_DIGEST")
    for lang in ["en", "fr"]:
        name = "report-" + lang + ".md"
        report = files.get(name, "")
        if not report.strip():
            fail("MISSING_BILINGUAL_REPORT", language=lang)
            continue
        for scope in raw["consumer"]["scopeSymbols"]:
            if scope not in report:
                fail("UNNAMED_CONSUMER_TEST_SCOPE", language=lang, scope=scope)
        for side in ["before", "after"]:
            if raw["dependency"][side]["version"] not in report:
                fail("UNNAMED_DEPENDENCY_VERSION", language=lang, side=side)
        if "test" not in report.lower() or ("unknown" not in report.lower() if lang == "en" else "inconnu" not in report.lower()):
            fail("MISSING_ACTION_OR_COST_QUALIFICATION", language=lang)
        if "HOLD" not in report or ("not behavioral validation" not in report.lower() if lang == "en" else "ni une validation comportementale" not in report.lower()):
            fail("MISSING_APPROVAL_BOUNDARY", language=lang)
        for call, truth in expected.items():
            snippet = ast.get_source_segment(consumer["text"], nodes[call])
            if call[2] not in report or f"L{call[0]}" not in report or snippet not in report or url(consumer, call[0]) not in report:
                fail("REPORT_MISSING_CALL_EVIDENCE", language=lang, call=list(call))
        for link in re.findall(r"\]\(([^)]+)\)", report):
            if "://" not in link and not link.startswith("#") and link not in files:
                fail("DANGLING_LOCAL_REFERENCE", language=lang, link=link)
    if pack.get("frozen", {}).get("sourceHash") != expected_source_hash:
        fail("WORKBENCH_SOURCE_IDENTITY")
    if pack.get("result", {}).get("evidence", {}).get("resultSha256") != result_sha:
        fail("WORKBENCH_RESULT_IDENTITY")
    evaluation = pack.get("evaluation", {})
    if evaluation.get("admission") != "HOLD" or evaluation.get("authority") != [] or evaluation.get("settlement") != "NOT_CONNECTED":
        fail("WORKBENCH_AUTHORITY_OR_SETTLEMENT")
    if inspection.get("activeAuthority") != [] or inspection.get("activeProof") != []:
        fail("IMPORTED_ACTIVE_AUTHORITY")
    return {"schema": "alpha-transfer-independent-complete-handoff-review/v1", "task": raw["id"], "arm": arm,
            "inputSha256": digest(raw), "proposalSha256": digest(proposal),
            "inventoryAccepted": structural["complete_truthful_inventory"], "completeHandoffAccepted": not errors,
            "requiredCalls": len(expected), "statusCounts": outcomes, "materialErrors": errors,
            "conservativeUnresolvedOnBindableSource": structural["conservative_unresolved_on_bindable_source"],
            "semanticReviewRequired": "A same-session post-seal reviewer must substantiate refusal reasons and practical recommendations, particularly where source-backed candidates were available. Text presence alone is not semantic proof.",
            "limits": ["Complete scoped source handoff is not observed customer acceptance, full runtime behavior, security or production approval.",
                       "Signatures are checked independently without upstream imports or executing captured source.",
                       "Four purposive jobs; calls and repeated arms are not independent maintenance jobs."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--arm", choices=["A", "B", "C"], required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads((ROOT / "tasks" / (args.task + ".json")).read_text())
    oracle = json.loads((ROOT / "oracle" / (args.task + ".json")).read_text())
    files = {p.name: p.read_text() for p in (args.package / "delivery").iterdir() if p.is_file()}
    proposal = json.loads(files["proposal.json"])
    pack = json.loads((args.package / "workbench-pack.json").read_text())
    inspection = json.loads((args.package / "workbench-inspection.json").read_text())
    expected_hash = json.loads((ROOT / "candidate-binding.json").read_text())["expectedWorkbenchSourceHash"]
    review = evaluate(raw, oracle, proposal, files, pack, inspection, expected_hash, args.arm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        handle.write(json.dumps(review, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"task": args.task, "arm": args.arm, "accepted": review["completeHandoffAccepted"], "defects": len(review["materialErrors"])}))


if __name__ == "__main__":
    main()

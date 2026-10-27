# SPDX-License-Identifier: Apache-2.0
"""Pre-release oracle controls; synthetic packets, never candidate outcomes."""
import ast
import copy
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from evaluate_handoff import canonical, digest, evaluate, url

ROOT = Path(__file__).resolve().parents[1]
expected_hash = json.loads((ROOT / "candidate-binding.json").read_text())["expectedWorkbenchSourceHash"]


def golden(raw, oracle):
    proposal = {"schema": "alpha-transfer-extraction/v1", "inputSha256": digest(raw), "claims": [], "unresolved": []}
    request = {"schema": "alpha-upgrade-call-request/v1", "id": raw["id"], "sources": raw["sources"], "calls": []}
    core = {"calls": []}
    inventory = []
    source = raw["sources"]["consumer"]
    nodes = {(n.lineno, n.col_offset, ast.unparse(n.func)): n for n in ast.walk(ast.parse(source["text"])) if isinstance(n, ast.Call)}
    for index, truth in enumerate(oracle["calls"]):
        loc = {k: truth[k] for k in ["line", "column", "callee"]}
        targets = {side: {k: truth["targets"][side][k] for k in ["source", "symbol"]} for side in ["before", "after"]}
        call_id = "synthetic-control-" + str(index)
        explanation = "Synthetic oracle control: conditional captured declaration, not candidate output or runtime proof."
        proposal["claims"].append({**loc, **targets, "explanation": explanation})
        request["calls"].append({"id": call_id, **loc, **targets, "mapping": {"kind": "declared-target", "explanation": explanation}})
        core["calls"].append({"id": call_id, "status": truth["expected_core_scope_outcome"],
                              **{side + "Accepts": truth["independent_argument_acceptance"][side] for side in ["before", "after"]}})
        inventory.append({"id": call_id, **loc, "status": truth["expected_core_scope_outcome"],
                          "mappingVerified": False, "reason": "Runtime dispatch/arguments require evidence.",
                          "snippet": ast.get_source_segment(source["text"], nodes[(loc["line"], loc["column"], loc["callee"])]),
                          "consumerSha256": source["sha256"], "consumerUrl": url(source, loc["line"]),
                          "targets": {side: {**target, "url": url(raw["sources"][target["source"]]),
                                              "sha256": raw["sources"][target["source"]]["sha256"]} for side, target in targets.items()}})
    result = {"inputSha256": digest(raw), "productionApproved": False, "actualCollectionsUsd": 0,
              "nextAction": "REVIEW_UNRESOLVED_SCOPE", "arm": "B", "request": request, "coreRecord": core,
              "resources": {"wallNs": 1, "cpuNs": 1, "completeDeliveryMoneyUsd": None},
              "handoff": {"inventorySha256": digest(inventory)}}
    costs = {"unknowns": ["all unmetered bills"], "completeCostsIdentified": False, "noWageConversion": True,
             "marginalUsd": None, "recurringUsd": None, "fullyLoadedUsd": None, "actualCollectionsUsd": 0}
    files = {name: canonical(value).decode() for name, value in {"raw-task.json": raw, "decision-record.json": core,
             "result.json": result, "costs.json": costs, "call-inventory.json": inventory}.items()}
    for lang in ["en", "fr"]:
        report = "Synthetic oracle control, not an executed customer packet. HOLD. "
        report += "not behavioral validation; unknown full cost; test consumer path.\n" if lang == "en" else "ni une validation comportementale; coût inconnu; test du chemin.\n"
        report += ", ".join(raw["consumer"]["scopeSymbols"]) + " " + raw["dependency"]["before"]["version"] + " " + raw["dependency"]["after"]["version"] + "\n"
        for row in inventory:
            report += f"{row['callee']} L{row['line']} [source]({row['consumerUrl']})\n```python\n{row['snippet']}\n```\n"
        report += "[record](decision-record.json) [input](raw-task.json) [costs](costs.json)"
        files["report-" + lang + ".md"] = report
    receipt = {"inputSha256": digest(raw), "resultSha256": digest(result)}
    files["receipt.json"] = canonical(receipt).decode()
    pack = {"frozen": {"sourceHash": expected_hash}, "result": {"evidence": {"resultSha256": digest(result)}},
            "evaluation": {"admission": "HOLD", "authority": [], "settlement": "NOT_CONNECTED"}}
    return proposal, files, pack, {"activeAuthority": [], "activeProof": []}


controls = []
for tid in ["F01", "F02", "F03", "F04"]:
    raw = json.loads((ROOT / "tasks" / (tid + ".json")).read_text())
    oracle = json.loads((ROOT / "oracle" / (tid + ".json")).read_text())
    original = golden(raw, oracle)
    names = ["gold", "missing-french", "wrong-target", "omitted-proposal-call", "empty-snippet",
             "dangling-link", "cost-zero", "unsafe-approval", "false-runtime-proof", "active-authority"]
    for name in names:
        proposal, files, pack, inspection = copy.deepcopy(original)
        if name == "missing-french":
            files.pop("report-fr.md")
        elif name == "wrong-target":
            proposal["claims"][0]["after"]["symbol"] = "invented_target"
        elif name == "omitted-proposal-call":
            proposal["claims"].pop(0)
        elif name in ["empty-snippet", "false-runtime-proof"]:
            inventory = json.loads(files["call-inventory.json"])
            inventory[0]["snippet" if name == "empty-snippet" else "mappingVerified"] = "" if name == "empty-snippet" else True
            files["call-inventory.json"] = canonical(inventory).decode()
        elif name == "dangling-link":
            files["report-en.md"] += "\n[missing cost](not-present.json)"
        elif name == "cost-zero":
            costs = json.loads(files["costs.json"]); costs["fullyLoadedUsd"] = 0
            files["costs.json"] = canonical(costs).decode()
        elif name == "unsafe-approval":
            result = json.loads(files["result.json"]); result["productionApproved"] = True
            files["result.json"] = canonical(result).decode()
            receipt = json.loads(files["receipt.json"]); receipt["resultSha256"] = digest(result)
            files["receipt.json"] = canonical(receipt).decode(); pack["result"]["evidence"]["resultSha256"] = digest(result)
        elif name == "active-authority":
            inspection["activeAuthority"] = ["operator"]
        review = evaluate(raw, oracle, proposal, files, pack, inspection, expected_hash, "B")
        correct = review["completeHandoffAccepted"] == (name == "gold")
        controls.append({"task": tid, "control": name, "expectedAccepted": name == "gold", "actualAccepted": review["completeHandoffAccepted"],
                         "passed": correct, "defectKinds": sorted({e["kind"] for e in review["materialErrors"]})})
        if not correct:
            raise AssertionError((tid, name, review))
with (ROOT / "oracle/control-results.json").open("x") as handle:
    handle.write(json.dumps({"controls": controls, "passed": sum(r["passed"] for r in controls),
                            "primaryExecutions": 0, "candidateInvocations": 0, "independentJobs": 4,
                            "scope": "Synthetic acceptance controls derived from private source oracle; not candidate outcomes or customer work."}, indent=2) + "\n")
print(f"{len(controls)} independent acceptance controls passed; no candidate executed.")

# SPDX-License-Identifier: Apache-2.0
"""Build the offline EN/FR financial demonstration from frozen saved evidence.

This presentation builder never imports a simulator or executes a production arm.
Exact embedded artifacts use deterministic gzip for size and preserve source bytes.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import html
import json
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "publication/AGI_ALPHA_Second_Investment_Demo.html"
TEMPLATE = ROOT / "tools/demo-template.html"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_bytes())


def paired(en, fr):
    return f'<span lang="en">{html.escape(en)}</span><span lang="fr">{html.escape(fr)}</span>'


def money(cents):
    if cents is None:
        return "Unknown"
    return ("−" if cents < 0 else "") + f"${abs(cents) / 100:,.2f}"


def main():
    started = time.perf_counter()
    cpu_started = time.process_time()
    raw_data = (ROOT / "publication/publication-data.json").read_bytes()
    source = json.loads(raw_data)
    files = {}
    verified = []

    def verify(path, expected):
        data = (ROOT / path).read_bytes()
        actual = sha(data)
        if actual != expected:
            raise ValueError(f"Source identity mismatch: {path}")
        verified.append({"path": path, "sha256": actual, "bytes": len(data)})
        return data

    for name, expected in source["source_files"].items():
        verify(name, expected)
    production_freeze = read("protocol/production-freeze.json")
    for row in production_freeze["files"]:
        verify(row["path"], row["sha256"])

    def embed(path, label_en=None, label_fr=None, expected=None):
        if path in files:
            return path
        data = verify(path, expected) if expected else (ROOT / path).read_bytes()
        files[path] = {
            "name": Path(path).name,
            "label": {"en": label_en or path, "fr": label_fr or label_en or path},
            "sha256": sha(data), "bytes": len(data), "encoding": "gzip+base64",
            "data": base64.b64encode(gzip.compress(data, compresslevel=9, mtime=0)).decode("ascii"),
        }
        return path

    effect = read("market/effect-profile.json")
    for arm in ["B", "C"]:
        name = f"protocol/asset-{arm}.json"
        embed(name, f"{arm} · Asset manifest", f"{arm} · Manifeste de la capacité", effect["arms"][arm]["assetSHA256"])
        for row in read(name)["files"]:
            label = {
                "production/retained.py": ("B · Retained worker source", "B · Source du programme conservé"),
                "production/workbench.mjs": ("B · SUCCESSOR Ω adapter", "B · Adaptateur SUCCESSOR Ω"),
                "production/verify.py": ("Independent verifier source", "Source du vérificateur indépendant"),
                "production/conventional.py": ("C · Conventional builder source", "C · Source conventionnelle"),
                "protocol/acceptance-contract.json": ("Frozen acceptance contract", "Contrat d’acceptation figé"),
            }.get(row["path"], (row["path"], row["path"]))
            embed(row["path"], *label, row["sha256"])

    artifacts = []
    cards = []
    production_rows = source["production_rows"]
    for row in production_rows:
        verify(row["result_path"], row["result_sha256"])
        verify(row["verification_path"], row["verification_sha256"])
        if row["arm"] != "B":
            continue
        result = read(row["result_path"])
        certificate = read(row["verification_path"])
        assert certificate["result_sha256"] == row["result_sha256"]
        assert certificate["job_sha256"] == row["job_sha256"]
        assert row["accepted"] and certificate["status"] == "COMPLETE"
        result_path = embed(row["result_path"], f"{row['family']} · Result", f"{row['family']} · Résultat", row["result_sha256"])
        cert_path = embed(row["verification_path"], f"{row['family']} · Certificate", f"{row['family']} · Certificat", row["verification_sha256"])
        witnesses = certificate["substantiated_witnesses"]
        artifacts.append({"family": row["family"], "mission": row["mission"],
                          "decision": row["decision"], "resultPath": result_path, "certificatePath": cert_path,
                          "wallSeconds": row["complete_service_wall_seconds"],
                          "cpuSeconds": row["inclusive_cpu_seconds"], "witnesses": witnesses})
        verdict = paired("Conflict", "Conflit") if row["decision"] == "CONFLICT" else paired("Consistent", "Cohérent")
        explanation = (
            paired(f"The proposed version {witnesses[0]['actual']} violates the declared minimum.",
                   f"La version proposée {witnesses[0]['actual']} ne satisfait pas le minimum déclaré.")
            if witnesses else paired("The declared root and active dependency constraints are satisfied.",
                                     "Les contraintes racines déclarées et les dépendances actives sont satisfaites.")
        )
        cards.append(f'''<article class="delivery-card">
          <div class="card-top"><span class="badge measured">{paired("Measured", "Mesuré")}</span>
          <span class="verdict {'conflict' if witnesses else 'consistent'}">{verdict}</span></div>
          <h3>{html.escape(row['family'])}</h3>
          <p>{explanation}</p>
          <p class="small">{paired("Accepted evidence · A, B and C agree", "Preuve acceptée · A, B et C concordent")}</p>
          <div class="actions"><button class="text-button" data-file-view="{cert_path}">{paired("Inspect certificate", "Examiner le certificat")}</button>
          <button class="text-button" data-file-download="{result_path}">{paired("Download result", "Télécharger le résultat")}</button></div>
          <button class="quiet-button" data-file-download="{cert_path}">{paired("Certificate JSON", "Certificat JSON")}</button>
        </article>''')

    for name, en, fr in [
        ("publication/paper.pdf", "Final paper · PDF", "Article final · PDF"),
        ("publication/publication-data.json", "Complete publication data", "Données complètes de publication"),
        ("market/campaign-protocol.json", "Registered economic protocol", "Protocole économique préenregistré"),
        ("market/cost-profiles.json", "Complete cost allocations", "Ventilation complète des coûts"),
        ("market/effect-profile.json", "Measured effect mapping", "Correspondance des effets mesurés"),
        ("market/upstream/protocol/external-sources.json", "Archived calibration sources", "Sources de calibration archivées"),
        ("protocol/production-freeze.json", "Frozen production identities", "Identités de production figées"),
        ("analysis/market-findings.json", "Complete economic analysis", "Analyse économique complète"),
        ("review/market-results-independent-review.json", "Independent saved-ledger audit", "Audit indépendant des registres sauvegardés"),
    ]:
        embed(name, en, fr)
    files["publication/paper.pdf"]["name"] = "AGI_ALPHA_Second_Investment_Paper.pdf"

    # All eight preselected arms A are the same immutable first-enterprise path.
    # Store that common branch once; the inline code restores each complete ledger.
    common_keys = ["A", "A_balances", "A_cash", "A_bills", "A_invoices"]
    common_first_branch = {key: source["representatives"][0][key] for key in common_keys}
    assert all(all(r[key] == common_first_branch[key] for key in common_keys)
               for r in source["representatives"])
    representatives = [{key: value for key, value in r.items() if key not in common_keys}
                       for r in source["representatives"]]

    groups = []
    for g in source["market_groups"]:
        groups.append({"id": g["groupId"], "condition": g["conditionId"], "cost": g["costProfileId"],
                       "policy": g["policyId"], "n": g["completedSeeds"],
                       "difference": g["causal"]["B_minus_A_projectInclusiveProfitCents"],
                       "enterpriseDifference": g["causal"]["B_minus_A_profitCents"],
                       "counts": g["arms"]["B"]["counts"],
                       "acceptedDifference": g["causal"]["B_minus_A_accepted"],
                       "BMinusC": g["causal"]["B_minus_C_projectInclusiveProfitCents"],
                       "AFullHistory": g["arms"]["A"]["enterpriseProfitCents"]})
    assert len(groups) == 80 and len(source["representatives"]) == 8 and len(artifacts) == 6
    ref = next(g for g in groups if g["id"] == "reference__reference__completed-research-replay")
    rep = next(r for r in source["representatives"] if r["cost_profile"] == "reference" and r["policy"] == "completed-research-replay")
    checkpoint = rep["first_decision"]["beforeSearch"]
    assert checkpoint["availableCents"] == 8274 and checkpoint["collectedCents"] == 34000
    app = {
        "schema": "agi-alpha-second-investment-offline-demo/v1",
        "basis": "Saved evidence only. All monetary histories are simulated; actual receipts are zero.",
        "publicationDataSHA256": sha(raw_data), "totals": source["totals"],
        "groups": groups, "representatives": representatives, "commonFirstBranch": common_first_branch,
        "costs": source["costs"], "conditions": source["protocol"]["conditions"],
        "production": source["production"], "artifacts": artifacts,
        "effect": effect, "sources": source["source_files"],
        "resourceNote": {"construction": "Post-outcome assistant-researcher presentation contribution",
                         "actualHumanMinutes": None, "modelAndToolFeesUSD": None,
                         "creditedFinancialBenefit": 0, "newPaidCommitments": 0,
                         "newMarketExecutions": 0},
    }
    template = TEMPLATE.read_text()
    substitutions = {
        "__APP_DATA__": json.dumps(app, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c"),
        "__EMBEDDED_FILES__": json.dumps(files, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c"),
        "__STATIC_PRODUCTION_CARDS__": "\n".join(cards),
        "__PUBLICATION_DATA_SHA256__": sha(raw_data),
        "__REFERENCE_MEAN__": money(ref["difference"]["mean"]),
        "__REFERENCE_P05__": money(ref["difference"]["p05"]),
        "__REFERENCE_P95__": money(ref["difference"]["p95"]),
        "__PRECHECKPOINT_DELIVERIES__": str(sum(i["week"] < 26 for i in rep["A_invoices"])),
    }
    for key, value in substitutions.items():
        assert template.count(key) > 0, key
        template = template.replace(key, value)
    OUTPUT.write_text(template)
    receipt = {
        "schema": "agi-alpha-second-investment-demo-build/v1",
        "builtAtUTC": datetime.now(timezone.utc).isoformat(),
        "output": str(OUTPUT.relative_to(ROOT)), "outputSHA256": sha(OUTPUT.read_bytes()),
        "outputBytes": OUTPUT.stat().st_size, "publicationDataSHA256": sha(raw_data),
        "generatorSHA256": sha(Path(__file__).read_bytes()), "templateSHA256": sha(TEMPLATE.read_bytes()),
        "inputHashChecks": verified, "embeddedFiles": [{k: f[k] for k in ["name", "sha256", "bytes"]} for f in files.values()],
        "marketGroups": len(groups), "representativeLedgers": len(app["representatives"]),
        "productionQuestions": len(artifacts), "productionExecutionsRepresented": 18,
        "newProductionExecutions": 0, "newMarketExecutions": 0, "networkRequests": 0,
        "buildWallSeconds": time.perf_counter() - started, "buildCPUSeconds": time.process_time() - cpu_started,
        "actualHumanMinutes": None, "modelToolFeesUSD": None, "newPaidCommitments": 0,
        "creditedFinancialBenefit": 0,
        "contribution": "Assistant-researcher-authored post-outcome presentation builder. Build timing excludes authoring and source inspection; authoring/tool costs remain unidentified, not zero. No economic experiment or frozen cost profile is changed.",
        "browserQA": "Separate verification receipt; build does not imply a rendered browser inspection.",
    }
    target = ROOT / "resources/demo/BUILD_RECEIPT.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    sequence = len(list(target.parent.glob("build-[0-9][0-9][0-9].json"))) + 1
    history = target.parent / f"build-{sequence:03d}.json"
    history.write_text(json.dumps(receipt, indent=2) + "\n")
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ["output", "outputBytes", "outputSHA256", "marketGroups", "representativeLedgers", "productionQuestions", "buildWallSeconds"]}))


if __name__ == "__main__":
    main()

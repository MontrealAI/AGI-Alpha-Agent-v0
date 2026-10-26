# SPDX-License-Identifier: Apache-2.0
"""Parameterize the retained first-delivery template; require a supplied disposition.

This is the researcher-assisted incumbent, not a human-without-AI benchmark.
The shared receipt checker is an independent quality gate, not a decision producer.
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import time


ROOT = Path(__file__).resolve().parents[1]
STATES = ("SCOPED_COMPONENT_PRESERVED", "COMPONENT_REGRESSION", "INCOMPLETE_HOLD")
PASS = "PRESERVED_WITHIN_COMPONENT_CONTRACT"
SPEC = importlib.util.spec_from_file_location("manual_shared_receipt_quality", ROOT / "src/conventional_package.py")
QUALITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUALITY)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def local(relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("REGISTERED_RELATIVE_PATH_REQUIRED")
    result = (ROOT / path).resolve()
    if not result.is_relative_to(ROOT):
        raise ValueError("STUDY_PATH_ESCAPE")
    return result


def pair_file(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("PAIR_PATH_ESCAPE")
    result = root / path
    if result.is_symlink() or not result.is_file():
        raise ValueError("PAIR_FILE_MISSING_OR_UNSAFE:" + relative)
    return result


def assemble(job, pair_root, out, disposition):
    started, cpu = time.perf_counter(), time.process_time()
    if out.exists():
        raise ValueError("OUTPUT_EXISTS")
    if disposition not in STATES or job.get("schema") != "alpha-component-job/v1":
        raise ValueError("JOB_OR_DISPOSITION_SCHEMA")
    pair_root = pair_root.resolve()
    pair = read(pair_root / "pair.json")
    job_path = pair_root / "job.json"
    if read(job_path) != job or pair.get("job_sha256") != digest(job_path):
        raise ValueError("JOB_PAIR_IDENTITY")
    worker, verifier = ROOT / "src/manual_probe.py", ROOT / "src/verify_component.py"
    inventory = read(ROOT / "protocol/incumbent-inventory.json")
    pinned = {row["path"]: row["sha256"] for row in inventory["files"]}
    errors = []
    for name in ("src/manual_probe.py", "src/verify_component.py", "src/measured_run.py", "curation/assemble_first_delivery.py"):
        if digest(ROOT / name) != pinned[name]:
            errors.append("incumbent_asset_changed:" + name)
    if (pair.get("schema") != "alpha-component-pair/v1" or pair.get("custody_complete") is not True
            or pair.get("worker_path") != "src/manual_probe.py" or pair.get("worker_sha256") != digest(worker)):
        errors.append("pair_or_manual_worker_custody")
    for row in pair.get("artifacts", []):
        path = pair_file(pair_root, row["path"])
        if digest(path) != row["sha256"] or path.stat().st_size != row["bytes"]:
            errors.append("pair_artifact_changed:" + row["path"])
    contract_path = local(job["contract"]["path"])
    contract = read(contract_path)
    if digest(contract_path) != job["contract"]["sha256"]:
        errors.append("contract_identity")
    consumer = local(job["consumer"]["directory"])
    for name in ("api", "models"):
        if digest(consumer / (name + ".py")) != job["consumer"][name + "_sha256"]:
            errors.append("consumer_identity:" + name)
    records, artifacts = {}, []
    for side in ("before", "after"):
        environment = local(job[side]["environment"])
        paths = {name: pair_file(pair_root, rel) for name, rel in pair["records"][side].items()}
        observed, verified = read(paths["observations"]), read(paths["verification"])
        receipts = {key: read(paths[key]) for key in ("execution", "verification_execution")}
        for label, receipt in receipts.items():
            if not any(row.get("sha256") == digest(job_path) and row.get("bytes") == job_path.stat().st_size
                       for row in receipt.get("input_identities_before", [])):
                errors.append(side + ":" + label + ":job_binding")
        shared = [contract_path, ROOT / "protocol/component-projections.json",
                  consumer / "api.py", consumer / "models.py", environment / "preparation.json"]
        errors.extend(QUALITY.receipt_check(
            receipts["execution"], shared + [worker, ROOT / "src/measured_run.py",
                                              environment / "requirements.lock", environment / "venv/bin/python"],
            paths["observations"], {0, 1}, side + ":manual-probe"))
        errors.extend(QUALITY.receipt_check(
            receipts["verification_execution"], shared + [verifier, paths["observations"], ROOT / "discovery/test_api_boundary.py"],
            paths["verification"], {0, 2}, side + ":independent-verifier"))
        if (verified.get("schema") != "independent-component-verification/v1"
                or verified.get("observations_sha256") != digest(paths["observations"])
                or verified.get("environment_manifest_sha256") != digest(environment / "preparation.json")
                or verified.get("contract_sha256") != digest(contract_path)
                or verified.get("projection_id") != "native-fastapi-bridge-v2"
                or verified.get("native_import_route") is not True
                or observed.get("versions") != job[side]["expected_versions"]
                or verified.get("environment_versions") != job[side]["expected_versions"]):
            errors.append(side + ":source_environment_or_verification_binding")
        records[side] = {"verification": verified, "environment": environment}
        artifacts.extend((path, "evidence/" + side + "-" + name.replace("_", "-") + ".json")
                         for name, path in paths.items())
        artifacts.extend([(environment / "requirements.lock", "evidence/" + side + ".lock"),
                          (environment / "preparation.json", "evidence/" + side + "-environment.json")])
    before, after = (records[side]["verification"] for side in ("before", "after"))
    supported = ("INCOMPLETE_HOLD" if errors or before.get("status") != PASS else
                 "SCOPED_COMPONENT_PRESERVED" if after.get("status") == PASS else
                 "COMPONENT_REGRESSION" if after.get("status") == "BEHAVIOR_MISMATCH" else "INCOMPLETE_HOLD")
    if disposition != supported:
        raise ValueError("MANUAL_DISPOSITION_UNSUPPORTED: requested=" + disposition + "; evidence_supports=" + supported)

    out.mkdir(parents=True, exist_ok=False)
    artifacts.extend([(job_path, "evidence/job.json"), (pair_root / "pair.json", "evidence/pair.json")])
    for relative in ("protocol/component-contract.json", "protocol/component-projections.json", "protocol/intent-charter.json",
                     "protocol/incumbent-inventory.json", "protocol/manual-incumbent-confirmation.md",
                     "src/manual_probe.py", "src/verify_component.py", "src/measured_run.py", "src/conventional_package.py",
                     "curation/assemble_first_delivery.py", "curation/assemble_manual_mission.py", "discovery/test_api_boundary.py"):
        artifacts.append((ROOT / relative, "evidence/" + Path(relative).name))
    artifacts.extend([(consumer / "api.py", "evidence/api.py"), (consumer / "models.py", "evidence/models.py")])
    artifacts.extend((path, "evidence/logs/" + path.name) for path in sorted(pair_root.glob("*.txt")))
    bindings = []
    for source, relative in artifacts:
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        bindings.append({"source": str(source), "package_path": relative, "sha256": digest(target), "bytes": target.stat().st_size})
    patch = "".join(difflib.unified_diff(
        (records["before"]["environment"] / "requirements.lock").read_text().splitlines(True),
        (records["after"]["environment"] / "requirements.lock").read_text().splitlines(True),
        fromfile="baseline-component.lock", tofile="proposed-component.lock"))
    (out / "proposed-component-lock.patch").write_text(patch)
    action = {
        "SCOPED_COMPONENT_PRESERVED": "Accept this finite component evidence for further qualification; keep the current native lock pending full application and release checks.",
        "COMPONENT_REGRESSION": "Hold the proposed component refresh, retain the verified baseline and reproduce the listed behavioral mismatches.",
        "INCOMPLETE_HOLD": "Do not accept this incomplete component assessment; resolve the recorded evidence or execution gaps before another decision.",
    }[disposition]
    remaining = ["Decide whether the refresh is needed for the maintained release.",
                 "Resolve and qualify the full application lock and supported platforms.",
                 "Run authorized whole-application authentication, journal persistence and mission-execution checks.",
                 "Obtain owner review and the existing exact-source release gates."]
    decision = {
        "schema": "alpha-component-decision/v1", "producer": "researcher-finalized-incumbent-template",
        "mission_id": job["mission_id"], "phase": job["phase"], "trigger": job["trigger"], "decision": disposition,
        "manual_disposition": {"supplied": disposition, "checked_against_verifier_evidence": True,
                               "meaning": "Root supplied this disposition after reviewing results; this is not a no-AI human benchmark or release authority."},
        "job_sha256": digest(job_path), "useful_action": action,
        "acceptance": "Common independent finite-contract quality gate; actual customer acceptance not observed.",
        "before_versions": job["before"]["expected_versions"], "after_versions": job["after"]["expected_versions"],
        "coverage": {"requirements": len(contract["cases"]), "before": before.get("counts"), "after": after.get("counts")},
        "verification_status": {"before": before.get("status"), "after": after.get("status")},
        "custody_errors": errors, "remaining_customer_work": remaining,
        "limits": contract["coverage_limits"] + ["The patch is a component research profile, not a qualified replacement for requirements-agent.lock.",
                                                "No production, operator or financial authorization is supplied."],
        "cost": {"marginal_money_usd": None, "recurring_money_usd": None, "fully_loaded_money_usd": None,
                 "customer_price_usd": None, "actual_customer_receipts_usd": 0, "operator_minutes": None,
                 "customer_minutes": None, "inference_cost_usd": None,
                 "pair_wall_seconds": pair.get("wall_seconds"), "pair_process_cpu_seconds": pair.get("process_cpu_seconds"),
                 "pair_child_cpu_seconds": pair.get("child_cpu_seconds"),
                 "assembly_cpu_seconds": time.process_time() - cpu,
                 "basis": "Retain construction, common quality-gate allocation, failures, researcher actions and complete service span separately; process elapsed time is not attention or money."},
        "retained_assets": {"original_assembler_sha256": digest(ROOT / "curation/assemble_first_delivery.py"),
                            "parameterized_assembler_sha256": digest(Path(__file__)),
                            "shared_receipt_quality_sha256": digest(ROOT / "src/conventional_package.py")},
        "evidence": bindings, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (out / "decision.json").write_text(json.dumps(decision, indent=2, allow_nan=False) + "\n")
    (out / "requirement-results.json").write_text(json.dumps({"before": before["cases"], "after": after["cases"]}, indent=2) + "\n")
    versions = "\n".join("| " + name + " | " + job["before"]["expected_versions"].get(name, "—") + " | "
                         + job["after"]["expected_versions"].get(name, "—") + " |"
                         for name in sorted(job["before"]["expected_versions"].keys() | job["after"]["expected_versions"].keys()))
    counts = (len(contract["cases"]), before.get("counts", {}).get("PASS", 0), after.get("counts", {}).get("PASS", 0))
    (out / "README.md").write_text(
        "# Dependency refresh: researcher-finalized incumbent assessment\n\n**" + disposition + "**\n\n" + action
        + "\n\nRequired cases: %s. Verified conforming cases: %s before, %s after.\n\n" % counts
        + "| Package | Before | Proposed |\n|---|---|---|\n" + versions
        + "\n\nRoot supplied the disposition after reviewing the exact common verifier outcomes. The retained assembly template "
        "and shared receipt checks refuse an unsupported disposition. This is researcher-assisted work, not measured no-AI human labor.\n\n"
        "## Remaining qualification\n\n" + "\n".join("- " + row for row in remaining)
        + "\n\nEvidence contains source, exact component locks, observations, execution receipts, complete requirement results and reproduction commands. "
        "The required scope includes the original FastAPI import bridge and real 15-second timeout; the recorded results show completion or gaps. No full application, credentials, Journal or operator "
        "action was created. Complete cost, price and attention remain unknown; customer receipts are zero. Cases and retries do not add customer jobs.\n")
    action_fr = {
        "SCOPED_COMPONENT_PRESERVED": "Accepter ces preuves limitées aux composants pour la qualification suivante ; conserver le verrou natif actuel jusqu'aux contrôles complets de l'application et de publication.",
        "COMPONENT_REGRESSION": "Suspendre la mise à jour proposée, conserver la configuration de référence vérifiée et reproduire les écarts de comportement indiqués.",
        "INCOMPLETE_HOLD": "Ne pas accepter cette évaluation incomplète ; résoudre les lacunes de preuves ou d'exécution avant une nouvelle décision.",
    }[disposition]
    (out / "README.fr.md").write_text(
        "# Mise à jour des dépendances : dossier finalisé par le chercheur\n\n**" + disposition + "**\n\n" + action_fr
        + "\n\nCas requis : %s. Cas vérifiés conformes : %s avant, %s après.\n\n" % counts
        + "| Paquet | Avant | Proposition |\n|---|---|---|\n" + versions
        + "\n\nLe responsable de l'étude a fourni la décision après examen des résultats exacts du vérificateur commun. "
        "Le modèle de dossier conservé et les contrôles de reçus refusent une décision non étayée. Ce travail assisté par le chercheur "
        "ne constitue pas une mesure du travail humain sans IA.\n\n## Qualification restante\n\n"
        "- Déterminer si la mise à jour est nécessaire pour la version maintenue.\n"
        "- Résoudre et qualifier toutes les dépendances de l'application et les plateformes prises en charge.\n"
        "- Exécuter les contrôles autorisés d'authentification, de persistance du journal et d'exécution des missions.\n"
        "- Obtenir la revue des responsables et satisfaire les exigences de publication liées au code source exact.\n\n"
        "Les preuves comprennent le code source, les verrous exacts des composants, les observations, les reçus d'exécution, "
        "les résultats détaillés et les commandes de reproduction. Le périmètre requis inclut le chemin d'importation FastAPI d'origine et le délai réel "
        "de 15 secondes ; les résultats indiquent les contrôles terminés ou les lacunes. Aucune application complète, aucun identifiant d'accès, Journal ou acte d'opérateur "
        "n'a été créé. Le coût complet, le prix et le temps d'attention restent inconnus ; les encaissements clients sont nuls. "
        "Les cas et les nouvelles tentatives ne constituent pas des missions clientes supplémentaires.\n")
    (out / "reproduce.txt").write_text(
        "Use the complete companion root and new output paths. Retain the original before/after execution argv in evidence/*execution.json.\n"
        "Run the preserved manual_probe.py under each exact environment, then the common independent verifier.\n"
        "Inspect those results and supply the supported disposition explicitly:\n"
        "python curation/assemble_manual_mission.py --job PATH_TO_JOB --pair-root NEW_PAIR_ROOT --out NEW_PACKAGE --decision CHOSEN_DISPOSITION\n"
        "The component patch is not a replacement for the full native application lock. Exact environments/wheels remain in the full companion.\n")
    files = [{"path": str(p.relative_to(out)), "sha256": digest(p), "bytes": p.stat().st_size}
             for p in sorted(out.rglob("*")) if p.is_file()]
    for entry in files:
        if digest(out / entry["path"]) != entry["sha256"]:
            raise ValueError("PACKAGE_INTEGRITY")
    (out / "artifact-manifest.json").write_text(json.dumps({"schema": "component-package-manifest/v1", "files": files,
        "assembly_wall_seconds": time.perf_counter() - started, "assembly_cpu_seconds": time.process_time() - cpu,
        "money_usd": None}, indent=2) + "\n")
    return decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("job", "pair-root", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--decision", choices=STATES, required=True)
    args = parser.parse_args()
    result = assemble(read(args.job), args.pair_root, args.out, args.decision)
    print(json.dumps({"decision": result["decision"], "custody_errors": result["custody_errors"], "out": str(args.out)}))


if __name__ == "__main__":
    main()

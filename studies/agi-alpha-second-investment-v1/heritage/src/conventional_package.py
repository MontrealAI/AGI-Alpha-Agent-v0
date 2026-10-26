# SPDX-License-Identifier: Apache-2.0
"""Ordinary independently implemented paired component assessment package.

Uses the shared execution controller and independent verifier as infrastructure;
does not import the retained candidate's producer or decision implementation.
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import time
import traceback


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_SHA256 = "fc002f8b13429585e97bc2c1216a4c666ca162dfeb9b509d10da34298b9950be"
PRESERVED = "PRESERVED_WITHIN_COMPONENT_CONTRACT"


def sha(path):
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


def inside(directory, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("PAIR_ARTIFACT_PATH_ESCAPE")
    result = directory / path
    if result.is_symlink() or not result.is_file():
        raise ValueError("MISSING_OR_UNSAFE_PAIR_ARTIFACT:" + relative)
    return result


def record_matches(entry, path):
    return (entry.get("sha256") == sha(path) and entry.get("bytes") == path.stat().st_size
            and Path(entry.get("path", "")).resolve() == path.resolve())


def receipt_check(receipt, inputs, output, allowed_exit_codes, label):
    errors = []
    if (receipt.get("schema") != "alpha-measured-command/v1"
            or receipt.get("command_started") is not True or receipt.get("timed_out") is not False
            or receipt.get("launcher_error") is not None
            or type(receipt.get("exit_code")) is not int or receipt["exit_code"] not in allowed_exit_codes
            or receipt.get("inputs_unchanged") is not True or receipt.get("missing_outputs") != []
            or receipt.get("input_identities_before") != receipt.get("input_identities_after")):
        errors.append(label + ":execution_receipt_incomplete")
    captured = receipt.get("input_identities_before", [])
    for target in inputs:
        if not any(record_matches(item, target) for item in captured):
            errors.append(label + ":unbound_input:" + target.name)
    if not any(record_matches(item, output) for item in receipt.get("output_identities", [])):
        errors.append(label + ":unbound_output")
    return errors


def _assemble(job, pair_root, output_dir):
    """Assemble exact records; an incomplete record always produces HOLD."""
    wall, cpu = time.perf_counter(), time.process_time()
    if output_dir.exists():
        raise ValueError("OUTPUT_EXISTS")
    pair_root = Path(pair_root).resolve()
    errors, artifacts, sides = [], [], {}
    pair_path, job_copy = pair_root / "pair.json", pair_root / "job.json"
    pair = read(pair_path)
    if read(job_copy) != job or pair.get("job_sha256") != sha(job_copy):
        errors.append("job_pair_identity")
    if job.get("schema") != "alpha-component-job/v1" or pair.get("schema") != "alpha-component-pair/v1":
        errors.append("job_or_pair_schema")
    if pair.get("arm") != "conventional" or pair.get("custody_complete") is not True:
        errors.append("pair_custody_or_arm")
    worker = ROOT / "src/conventional_probe.py"
    verifier = ROOT / "src/verify_component.py"
    if pair.get("worker_path") != "src/conventional_probe.py" or pair.get("worker_sha256") != sha(worker):
        errors.append("worker_identity")
    if sha(verifier) != VERIFIER_SHA256:
        errors.append("independent_verifier_identity")
    contract_path = local(job["contract"]["path"])
    contract = read(contract_path)
    if sha(contract_path) != job["contract"]["sha256"]:
        errors.append("contract_identity")
    consumer = local(job["consumer"]["directory"])
    for name in ("api", "models"):
        if sha(consumer / (name + ".py")) != job["consumer"][name + "_sha256"]:
            errors.append("consumer_identity:" + name)
    for item in pair.get("artifacts", []):
        path = inside(pair_root, item["path"])
        if sha(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            errors.append("pair_manifest_identity:" + item["path"])
    for side in ("before", "after"):
        environment = local(job[side]["environment"])
        records = {key: inside(pair_root, name) for key, name in pair["records"][side].items()}
        observed, verified = read(records["observations"]), read(records["verification"])
        execution, scrutiny = read(records["execution"]), read(records["verification_execution"])
        for label, receipt in (("probe", execution), ("verifier", scrutiny)):
            if not any(item.get("sha256") == sha(job_copy) and item.get("bytes") == job_copy.stat().st_size
                       for item in receipt.get("input_identities_before", [])):
                errors.append(side + ":" + label + ":job_input_binding")
        preparation = environment / "preparation.json"
        lock = environment / "requirements.lock"
        inputs = [worker, ROOT / "src/measured_run.py", contract_path,
                  ROOT / "protocol/component-projections.json", consumer / "api.py", consumer / "models.py",
                  lock, preparation, environment / "venv/bin/python"]
        errors.extend(receipt_check(execution, inputs, records["observations"], {0, 1}, side + ":probe"))
        inputs = [verifier, contract_path, ROOT / "protocol/component-projections.json", records["observations"],
                  consumer / "api.py", consumer / "models.py", ROOT / "discovery/test_api_boundary.py", preparation]
        errors.extend(receipt_check(scrutiny, inputs, records["verification"], {0, 2}, side + ":verifier"))
        if (verified.get("schema") != "independent-component-verification/v1"
                or verified.get("observations_sha256") != sha(records["observations"])
                or verified.get("environment_manifest_sha256") != sha(preparation)
                or verified.get("contract_sha256") != sha(contract_path)
                or verified.get("projection_id") != "native-fastapi-bridge-v2"
                or verified.get("native_import_route") is not True):
            errors.append(side + ":verification_identity")
        if observed.get("versions") != job[side]["expected_versions"] or verified.get("environment_versions") != job[side]["expected_versions"]:
            errors.append(side + ":environment_version_identity")
        if observed.get("producer") != "independent-stdlib-unittest":
            errors.append(side + ":conventional_producer_identity")
        sides[side] = {"observed": observed, "verified": verified, "environment": environment,
                       "execution": execution, "verification_execution": scrutiny}
        for key, path in records.items():
            artifacts.append((path, "evidence/" + side + "-" + key.replace("_", "-") + ".json"))
        artifacts.extend([(lock, "evidence/" + side + ".lock"),
                          (preparation, "evidence/" + side + "-environment.json")])

    first, second = sides["before"]["verified"], sides["after"]["verified"]
    if errors or first.get("status") != PRESERVED:
        decision = "INCOMPLETE_HOLD"
    elif second.get("status") == PRESERVED:
        decision = "SCOPED_COMPONENT_PRESERVED"
    elif second.get("status") == "BEHAVIOR_MISMATCH":
        decision = "COMPONENT_REGRESSION"
    else:
        decision = "INCOMPLETE_HOLD"
    action = {
        "SCOPED_COMPONENT_PRESERVED": "Accept this finite component evidence for further qualification; keep the current native lock pending full-application and release checks.",
        "COMPONENT_REGRESSION": "Hold this proposed component refresh, retain the verified baseline and reproduce the listed mismatches before considering a remedy.",
        "INCOMPLETE_HOLD": "Do not accept the proposed component work package; resolve the listed evidence or execution gaps and rerun the required checks.",
    }[decision]
    artifacts.extend([(job_copy, "evidence/job.json"), (pair_path, "evidence/pair.json"),
                      (contract_path, "evidence/component-contract.json"),
                      (ROOT / "protocol/component-projections.json", "evidence/component-projections.json"),
                      (ROOT / "protocol/intent-charter.json", "evidence/intent-charter.json"),
                      (consumer / "api.py", "evidence/api.py"), (consumer / "models.py", "evidence/models.py"),
                      (ROOT / "discovery/test_api_boundary.py", "evidence/test_api_boundary.py"),
                      (worker, "evidence/conventional_probe.py"), (Path(__file__), "evidence/conventional_package.py"),
                      (verifier, "evidence/verify_component.py"),
                      (ROOT / "src/run_pair.py", "evidence/run_pair.py"),
                      (ROOT / "src/measured_run.py", "evidence/measured_run.py")])
    for path in sorted(pair_root.glob("*.txt")):
        artifacts.append((path, "evidence/logs/" + path.name))
    output_dir.mkdir(parents=True, exist_ok=False)
    copied = []
    for path, target in artifacts:
        destination = output_dir / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        copied.append({"source": str(path), "package_path": target,
                       "sha256": sha(destination), "bytes": destination.stat().st_size})
    patch = "".join(difflib.unified_diff(
        (sides["before"]["environment"] / "requirements.lock").read_text().splitlines(True),
        (sides["after"]["environment"] / "requirements.lock").read_text().splitlines(True),
        fromfile="before/component.lock", tofile="proposed/component.lock"))
    (output_dir / "proposed-component-lock.patch").write_text(patch)
    remaining = [
        "Decide whether this proposed refresh is needed for the maintained release.",
        "Resolve and qualify the full application dependency lock and supported platform matrix.",
        "Run separately authorized whole-application authentication, journal persistence and mission-execution checks.",
        "Obtain existing owner review and exact-source release gates before adoption.",
    ]
    result = {
        "schema": "alpha-component-decision/v1", "producer": "independent-conventional-unittest-package",
        "mission_id": job["mission_id"], "phase": job["phase"], "decision": decision,
        "trigger": job["trigger"], "job_sha256": sha(job_copy), "useful_action": action,
        "acceptance": "Independent internal finite-contract verification; customer acceptance not observed.",
        "before_versions": job["before"]["expected_versions"], "after_versions": job["after"]["expected_versions"],
        "coverage": {"requirements": len(contract["cases"]), "before": first.get("counts"), "after": second.get("counts")},
        "verification_status": {"before": first.get("status"), "after": second.get("status")},
        "custody_errors": errors, "remaining_customer_work": remaining,
        "limits": contract["coverage_limits"] + ["Component lock patch is a research profile, not a replacement for the full native application lock.",
                                                "No production, financial or operator authority; no paid order is asserted."],
        "cost": {"marginal_money_usd": None, "recurring_money_usd": None, "fully_loaded_money_usd": None,
                 "actual_customer_receipts_usd": 0, "customer_price_usd": None, "customer_minutes": None,
                 "operator_minutes": None, "pair_wall_seconds": pair.get("wall_seconds"),
                 "pair_process_cpu_seconds": pair.get("process_cpu_seconds"), "pair_child_cpu_seconds": pair.get("child_cpu_seconds"),
                 "assembly_cpu_seconds": time.process_time() - cpu,
                 "basis": "Primitive process quantities only; construction/shared infrastructure/maintenance and unknown inference/attention costs remain in the complete study ledger."},
        "evidence": copied, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (output_dir / "decision.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output_dir / "requirement-results.json").write_text(json.dumps(
        {"before": first["cases"], "after": second["cases"]}, indent=2) + "\n")
    version_rows = "\n".join(
        "| " + name + " | " + job["before"]["expected_versions"].get(name, "—") + " | "
        + job["after"]["expected_versions"].get(name, "—") + " |"
        for name in sorted(job["before"]["expected_versions"].keys() | job["after"]["expected_versions"].keys()))
    before_count, after_count = first.get("counts", {}).get("PASS", 0), second.get("counts", {}).get("PASS", 0)
    required_count = len(contract["cases"])
    (output_dir / "README.md").write_text(
        "# Dependency refresh: conventional component assessment\n\n**" + decision + "**\n\n" + action
        + f"\n\nRequired cases: {required_count}. Verified cases: {before_count} before, {after_count} after.\n\n"
        "| Package | Before | Proposed |\n|---|---|---|\n" + version_rows
        + "\n\nThe original component definitions and FastAPI import bridge were tested with a reusable ordinary unittest suite. "
        "The shared independent verifier checks all required observations. Required assertions, environment repetitions and "
        "invalid-input rejection cases are not separate customer jobs or production defects.\n\n"
        "## Remaining qualification\n\n" + "\n".join("- " + item for item in remaining)
        + "\n\nThe exact component locks, sources, observations, process receipts, verifier and implementation are in evidence/. "
        "The full companion supplies the preserved wheel environments. The patch does not replace requirements-agent.lock. "
        "No credentials, Journal, full application or operator action was created. All monetary cost, price and attention estimates remain unknown; actual receipts are zero.\n")
    french_action = {
        "SCOPED_COMPONENT_PRESERVED": "Accepter ces preuves limitées aux composants pour la qualification suivante ; conserver le verrou natif actuel jusqu'aux contrôles de l'application complète et de publication.",
        "COMPONENT_REGRESSION": "Suspendre cette proposition de mise à jour, conserver la configuration de référence vérifiée et reproduire les écarts indiqués avant d'envisager une correction.",
        "INCOMPLETE_HOLD": "Ne pas accepter ce dossier de compatibilité ; résoudre les lacunes de preuves ou d'exécution indiquées, puis relancer les contrôles requis.",
    }[decision]
    (output_dir / "README.fr.md").write_text(
        "# Mise à jour des dépendances : évaluation conventionnelle des composants\n\n**" + decision + "**\n\n"
        + french_action + f"\n\nCas requis : {required_count}. Cas vérifiés conformes : {before_count} avant, {after_count} après.\n\n"
        "| Paquet | Avant | Proposition |\n|---|---|---|\n" + version_rows
        + "\n\nLes définitions d'origine des composants et leur chemin d'importation FastAPI ont été exécutés au moyen "
        "d'une suite réutilisable de tests unittest. Le vérificateur indépendant commun contrôle les observations requises. "
        "Les assertions, les environnements répétés et les rejets attendus d'entrées invalides ne constituent ni des missions "
        "clientes distinctes ni des défauts de production découverts.\n\n## Qualification restante\n\n"
        "- Déterminer si cette mise à jour est nécessaire pour la version maintenue.\n"
        "- Résoudre et qualifier toutes les dépendances de l'application et les plateformes prises en charge.\n"
        "- Exécuter les contrôles autorisés de l'application complète : authentification, persistance du journal et exécution des missions.\n"
        "- Obtenir la revue des responsables et satisfaire les exigences de publication liées au code source exact.\n\n"
        "Les verrous exacts des composants, le code source, les observations, les reçus d'exécution, le vérificateur et "
        "l'implémentation figurent dans evidence/. Le compagnon complet fournit les environnements et les fichiers wheel "
        "conservés. Le correctif proposé ne remplace pas requirements-agent.lock. Aucun identifiant d'accès, Journal, "
        "application complète ou acte d'opérateur n'a été créé. Les coûts monétaires complets, le prix et le temps d'attention "
        "restent inconnus ; les encaissements clients réels sont nuls. La conformité des composants ne vaut pas autorisation de publication.\n")
    (output_dir / "reproduce.txt").write_text(
        "From the complete companion root, use the preserved environments and a new output destination:\n"
        "python src/run_pair.py --job PATH_TO_JOB --arm conventional --out NEW_PAIR_DIRECTORY\n"
        "python src/conventional_package.py --job PATH_TO_JOB --pair-root NEW_PAIR_DIRECTORY --out NEW_PACKAGE_DIRECTORY\n"
        "The package job is evidence/job.json. Environment/source paths in it are relative to the complete study root.\n")
    manifest = [{"path": str(path.relative_to(output_dir)), "sha256": sha(path), "bytes": path.stat().st_size}
                for path in sorted(output_dir.rglob("*")) if path.is_file()]
    (output_dir / "artifact-manifest.json").write_text(json.dumps({
        "schema": "component-package-manifest/v1", "files": manifest,
        "assembly_wall_seconds": time.perf_counter() - wall,
        "assembly_cpu_seconds": time.process_time() - cpu, "money_usd": None,
    }, indent=2) + "\n")
    return result


def assemble(job, pair_root, output_dir):
    """Preserve a failed assembly as an explicit incomplete decision package."""
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError("OUTPUT_EXISTS")
    started, cpu = time.perf_counter(), time.process_time()
    try:
        return _assemble(job, pair_root, output_dir)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        output_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "schema": "alpha-component-decision/v1", "producer": "independent-conventional-unittest-package",
            "mission_id": job.get("mission_id"), "phase": job.get("phase"), "decision": "INCOMPLETE_HOLD",
            "useful_action": "Do not accept this work package; repair the recorded missing or invalid evidence and rerun.",
            "custody_errors": [f"{type(exc).__name__}: {exc}"], "traceback": traceback.format_exc(),
            "pair_root": str(pair_root), "assembly_wall_seconds": time.perf_counter() - started,
            "assembly_cpu_seconds": time.process_time() - cpu, "money_usd": None,
            "authority": "No release, operator or financial authorization.",
        }
        (output_dir / "decision.json").write_text(json.dumps(result, indent=2) + "\n")
        (output_dir / "README.md").write_text(
            "# Incomplete component evidence\n\nThe work package is on hold. See decision.json for the exact failure. "
            "The original pair directory is preserved; no positive compatibility conclusion is available.\n")
        (output_dir / "README.fr.md").write_text(
            "# Preuves de compatibilité incomplètes\n\nLe dossier est suspendu. Le fichier decision.json indique l'échec exact. "
            "Le répertoire d'origine des exécutions est conservé ; aucune conclusion positive de compatibilité n'est disponible.\n")
        files = [{"path": str(p.relative_to(output_dir)), "sha256": sha(p), "bytes": p.stat().st_size}
                 for p in sorted(output_dir.rglob("*")) if p.is_file() and p.name != "artifact-manifest.json"]
        (output_dir / "artifact-manifest.json").write_text(json.dumps(
            {"schema": "component-package-manifest/v1", "files": files}, indent=2) + "\n")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--pair-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = assemble(read(args.job), args.pair_root, args.out)
    print(json.dumps({"decision": result["decision"], "custody_errors": result["custody_errors"], "out": str(args.out)}))
    raise SystemExit(0 if result["decision"] == "SCOPED_COMPONENT_PRESERVED" else 2)


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

try:
    from .acceptance import ROOT, canonical, check_completed_packet, in_study, mission_key, read_json, sha256, validate_job
except ImportError:
    from acceptance import ROOT, canonical, check_completed_packet, in_study, mission_key, read_json, sha256, validate_job

PRESERVED = {
    "production/incumbent.py": "a84749b2ca63902d3ab2a86c78bb599d651c427707ebc1193c1622c5ca95890f",
    "production/retained.py": "9d223262ab58043c6d03da24384c13d75f362547d72a5d94bf662f75e9a7f471",
    "production/verify.py": "583bc6d7cb5736d6805ceb87407fcf1b3c234de813aad1fba38270d875cfb586",
    "production/workbench.mjs": "450df8c140e35d89a9777be7e2d884d0b9a13004c37aa6a4c0bbd4bc76289414",
    "protocol/acceptance-contract.json": "507c1bcf5b6d03be727d69a6fd8354936ae9bab7e1b554acbd418a44f927e117",
}


def save(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")


def source_identity() -> dict[str, Any]:
    entries = []
    for relative, expected in PRESERVED.items():
        path = in_study(ROOT / relative)
        observed = sha256(path)
        if observed != expected:
            raise ValueError("PRESERVED_SOURCE_CHANGED:" + relative)
        entries.append({"path": relative, "sha256": observed, "bytes": path.stat().st_size})
    native = read_json(ROOT / "native/SOURCE.json")
    for row in native["files"]:
        path = in_study(ROOT / "native" / row["path"])
        observed = sha256(path)
        if observed != row["sha256"] or path.stat().st_size != row["bytes"]:
            raise ValueError("NATIVE_SOURCE_CHANGED")
        entries.append({"path": "native/" + row["path"], "sha256": observed, "bytes": row["bytes"]})
    for relative in ("src/production.py", "src/acceptance.py"):
        path = ROOT / relative
        entries.append({"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size})
    return {"schema": "verified-capability-production-source/v1", "files": entries,
            "sha256": hashlib.sha256(canonical(entries)).hexdigest()}


def invoke(command: list[str], folder: Path, label: str, *, allowed: tuple[int, ...] = (0,)) -> dict[str, Any]:
    started = time.perf_counter()
    environment = dict(os.environ, PYTHON_EXECUTABLE=sys.executable)
    with (folder / (label + ".stdout.txt")).open("x") as stdout, (folder / (label + ".stderr.txt")).open("x") as stderr:
        try:
            process = subprocess.run(command, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr,
                                     timeout=150, check=False)
            code = process.returncode
        except subprocess.TimeoutExpired:
            stderr.write("BOUNDED_OPERATION_TIMEOUT; no retry\n")
            code = 124
    receipt = {"command": command, "returncode": code, "accepted_exit": code in allowed,
               "wall_seconds": time.perf_counter() - started, "retry_count": 0,
               "stdout_sha256": sha256(folder / (label + ".stdout.txt")),
               "stderr_sha256": sha256(folder / (label + ".stderr.txt"))}
    save(folder / (label + ".command.json"), receipt)
    return receipt


def report(packet: dict[str, Any], language: str) -> str:
    fr = language == "fr"
    title = "Décision sur les métadonnées du verrou" if fr else "Complete-lock metadata decision"
    decision = packet["decision"]
    actions = {
        "CONSISTENT": ("Conserver ce dossier pour les tests comportementaux, de sécurité et de qualification de l’application.",
                       "Carry this packet into the application's behavioral, security and release qualification."),
        "CONFLICT": ("Suspendre cette proposition. Examiner les contraintes contradictoires ci-dessous avant de proposer un autre verrou.",
                     "Hold this proposal. Inspect the contradictory constraints below before proposing another lock."),
        "INCOMPLETE": ("Ne pas conclure. Rétablir les preuves manquantes ou corriger la portée, puis refaire la vérification.",
                       "Do not conclude. Restore missing evidence or correct the declared scope, then revalidate."),
    }
    certificate = packet.get("certificate", {})
    witnesses = certificate.get("substantiated_witnesses", [])
    text = [f"# {title}", "", f"**{decision}**", "", actions[decision][0 if fr else 1], "",
            f"Mission: `{packet.get('mission_key')}`", f"Input: `{packet.get('job_sha256')}`",
            f"Production source: `{packet.get('source_sha256')}`", "",
            "## Preuves / Evidence", "",
            "| Élément / Item | Valeur / Value |", "| --- | --- |",
            f"| Complete independent metadata certificate | {certificate.get('status', 'INCOMPLETE')} |",
            f"| Selected distributions | {certificate.get('evidence', {}).get('active_lock_count', 'unknown')} |",
            f"| Checked dependency relationships | {len(certificate.get('dependency_edges', []))} |",
            f"| Substantiated conflicts | {len(witnesses)} |",
            f"| Native history | {packet.get('route')} |", ""]
    if witnesses:
        text += ["## Contraintes contradictoires / Conflicting constraints", ""]
        text += ["- `" + json.dumps(w, ensure_ascii=False, sort_keys=True).replace("`", "'") + "`" for w in witnesses]
        text.append("")
    if packet.get("errors"):
        text += ["## Preuves incomplètes / Incomplete evidence", ""]
        text += ["- " + str(error) for error in packet["errors"]]
        text.append("")
    if fr:
        text += ["## Portée et coût", "", "Les vrais outils pip et le vérificateur inspectent les métadonnées de roues publiques archivées. "
                 "Aucune roue n’est installée et aucun code applicatif n’est exécuté. Ce résultat ne qualifie ni le comportement, "
                 "ni la sécurité, ni la publication de l’application. Les mesures locales de calcul ne sont pas des économies monétaires. "
                 "L’attention humaine, les appels d’inférence de construction, l’intégration et l’entretien restent inconnus. "
                 "Acceptation commerciale non observée; recettes réelles : 0. L’identité ENS en direct n’a pas été exécutée."]
    else:
        text += ["## Scope and cost", "", "Real pip and the independent verifier inspect archived public wheel metadata. "
                 "No wheel is installed and no application code is executed. This result does not qualify application behavior, "
                 "security or release. Local compute measurements are not monetary savings. Human attention, authoring inference, "
                 "integration and maintenance remain unknown. Customer acceptance is unobserved; actual receipts are 0. "
                 "Live ENS identity enforcement is NOT RUN."]
    return "\n".join(text) + "\n"


def run_pipeline(job_path: str | Path, output_path: str | Path, *, route: str = "native") -> dict[str, Any]:
    if route not in {"native", "direct"}:
        raise ValueError("REGISTERED_ROUTE_REQUIRED")
    output = in_study(Path(output_path), must_exist=False)
    output.mkdir(parents=True, exist_ok=False)
    start_wall, start_cpu = time.perf_counter(), time.process_time()
    child0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    commands: list[dict[str, Any]] = []
    errors: list[str] = []
    packet: dict[str, Any] = {"schema": "agi-alpha-verified-capability-packet/v1", "accepted": False,
                             "decision": "INCOMPLETE", "route": route, "application_qualified": False,
                             "authority": [], "financial_action": False, "new_customer_orders": 0,
                             "actual_collections": 0, "customer_acceptance": None, "human_minutes": None,
                             "customer_minutes": None, "live_identity_enforcement": "NOT_RUN"}
    try:
        job_path = in_study(Path(job_path))
        job, paths = validate_job(job_path)
        source = source_identity()
        save(output / "source-identity.json", source)
        packet.update(job_id=job["id"], job_sha256=sha256(job_path), mission_key=mission_key(job_path),
                      source_sha256=source["sha256"], target_environment=job["target_environment"])
        for name, path in (("job.json", job_path), ("requirements.lock", paths["lock_path"]),
                           ("pyproject.toml", paths["pyproject_path"])):
            (output / name).write_bytes(path.read_bytes())
        run = output / "execution"
        if route == "native":
            node = shutil.which("node")
            if not node:
                raise ValueError("NODE_UNAVAILABLE")
            commands.append(invoke([node, str(ROOT / "production/workbench.mjs"), str(job_path), str(run)], output, "native"))
        else:
            run.mkdir()
            commands.append(invoke([sys.executable, str(ROOT / "production/incumbent.py"), "--job", str(job_path),
                                    "--out", str(run / "delivery")], output, "direct"))
            if (run / "delivery/result.json").is_file():
                commands.append(invoke([sys.executable, str(ROOT / "production/verify.py"), "--job", str(job_path),
                                        "--result", str(run / "delivery/result.json"), "--out", str(run / "verification.json")],
                                       output, "independent", allowed=(0, 2)))
        if any(not command["accepted_exit"] for command in commands):
            raise ValueError("PRODUCTION_COMMAND_FAILED")
        checked = check_completed_packet(job_path, run, native=route == "native")
        packet.update(checked)
        packet["review"] = {
            "creator": "Unchanged retained ordinary-pip producer" if route == "native" else "Unchanged direct ordinary-pip incumbent",
            "critic": "Deterministic project/root and tool-result checks; no model or organizational independence claim",
            "critic_findings": packet["result"].get("preflight_findings", packet["result"].get("root_conflicts", [])),
            "verifier": "Independent implementation recomputes actual wheel metadata closure and reconciles the actual pip report",
            "verifier_substantiated_witnesses": packet["certificate"].get("substantiated_witnesses", []),
            "corrections": [], "no_finding_allowed": True, "all_compute_included": True,
        }
        if sha256(job_path) != packet["job_sha256"] or source_identity() != source:
            raise ValueError("SOURCE_OR_JOB_CHANGED_DURING_EXECUTION")
        validate_job(job_path)
        packet["native_history"] = {"path": "execution/pack.json", "admission": "HOLD",
                                    "authentication": "UNAUTHENTICATED_HISTORICAL_IMPORT"} if route == "native" else None
        packet["evidence_ids"] = {
            "result": sha256(run / "delivery/result.json"), "certificate": sha256(run / "verification.json"),
            "job": sha256(job_path), "source": source["sha256"],
        }
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
        errors.append(type(error).__name__ + ": " + str(error))
        packet.update(accepted=False, decision="INCOMPLETE")
    packet["errors"] = errors + packet.get("certificate", {}).get("errors", [])
    packet["commands"] = commands
    packet["measurement_scope"] = "Complete local preparation, production, independent metadata verification, source custody and common report/ZIP packaging; selector overhead outside this function is separately measured."
    packet["tools"] = {"model_calls": 0, "network_requests": 0,
                       "pip_resolutions": int(bool(packet.get("result", {}).get("commands"))),
                       "metadata_verifications": int("certificate" in packet),
                       "outer_subprocesses": len(commands), "retries": 0}
    for language in ("en", "fr"):
        (output / f"report.{language}.md").write_text(report(packet, language), encoding="utf-8")
    payload_files = [p for p in output.rglob("*") if p.is_file() and "selected-wheels" not in p.parts]
    payload_files.sort()
    payload = [{"path": str(p.relative_to(output)), "sha256": sha256(p), "bytes": p.stat().st_size} for p in payload_files]
    save(output / "payload-manifest.json", {"files": payload,
         "omitted_input_cache": "execution/delivery/selected-wheels duplicates exact source wheels already bound by job and certificate; full source wheels remain in companion inputs/wheels"})
    with zipfile.ZipFile(output / "decision-packet.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in payload_files + [output / "payload-manifest.json"]:
            archive.write(path, path.relative_to(output))
    child1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    packet["timings"] = {"complete_wall_seconds": time.perf_counter() - start_wall,
                          "inclusive_cpu_seconds": time.process_time() - start_cpu + child1.ru_utime + child1.ru_stime - child0.ru_utime - child0.ru_stime,
                          "producer_wall_seconds": packet.get("result", {}).get("elapsed_wall_seconds"),
                          "producer_cpu_seconds": packet.get("result", {}).get("cpu_seconds"),
                          "verifier_wall_seconds": packet.get("certificate", {}).get("verifier", {}).get("wall_seconds")}
    packet["packet_zip"] = {"path": "decision-packet.zip", "sha256": sha256(output / "decision-packet.zip"),
                            "bytes": (output / "decision-packet.zip").stat().st_size}
    packet["output_manifest_sha256"] = sha256(output / "payload-manifest.json")
    save(output / "packet.json", packet)
    return packet


def run_direct_pipeline(job_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    return run_pipeline(job_path, output_path, route="direct")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--route", choices=("native", "direct"), default="native")
    args = parser.parse_args()
    result = run_pipeline(args.job, args.out, route=args.route)
    print(json.dumps({k: result[k] for k in ("accepted", "decision", "route", "timings", "errors")}))
    raise SystemExit(0 if result["accepted"] else 2)

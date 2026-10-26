# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import platform
import resource
import signal
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml

STUDY = Path(__file__).resolve().parents[1]
ARM_MODES = {"B": "admitted-full", "C": "registry", "D": "graph"}


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".pending")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def children_cpu() -> float:
    used = resource.getrusage(resource.RUSAGE_CHILDREN)
    return used.ru_utime + used.ru_stime


def verify_freeze(root: Path, path: Path, identity: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ValueError("SOURCE_FREEZE_UNAVAILABLE") from error
    if sha(raw) != identity:
        raise ValueError("SOURCE_FREEZE_IDENTITY")
    manifest = json.loads(raw)
    if not isinstance(manifest.get("files"), list) or not manifest["files"]:
        raise ValueError("SOURCE_FREEZE_SCHEMA")
    names: set[str] = set()
    repository = root.parents[1].resolve()
    for item in manifest["files"]:
        if not isinstance(item, dict) or not {"path", "bytes", "sha256"}.issubset(item):
            raise ValueError("SOURCE_FREEZE_SCHEMA")
        relative = item["path"]
        if relative in names or Path(relative).is_absolute():
            raise ValueError("SOURCE_FREEZE_DUPLICATE_OR_ABSOLUTE")
        names.add(relative)
        candidate = root / relative
        source = candidate.resolve()
        if not source.is_relative_to(repository) or candidate.is_symlink():
            raise ValueError("SOURCE_FREEZE_BOUNDARY")
        try:
            data = source.read_bytes()
        except OSError as error:
            raise ValueError("SOURCE_CUSTODY_FAILED:" + relative) from error
        if len(data) != item["bytes"] or sha(data) != item["sha256"]:
            raise ValueError("SOURCE_CUSTODY_FAILED:" + relative)
    return {"sha256": identity, "files": len(names), "checkedAt": now(), "accepted": True}


def selected_pairs(protocol: dict[str, Any], phase: str) -> list[list[str]]:
    if phase == "all":
        return list(protocol["primary_pairs"] + protocol["transfer_pairs"])
    return list(protocol[phase + "_pairs"])


def normalized_yaml(raw: bytes) -> dict[str, Any]:
    class JsonLoader(yaml.SafeLoader):
        pass

    JsonLoader.yaml_implicit_resolvers = {
        key: [(tag, expression) for tag, expression in values if tag != "tag:yaml.org,2002:timestamp"]
        for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }
    parsed = yaml.load(raw, Loader=JsonLoader)
    ancestors: set[int] = set()

    def convert(value: Any) -> Any:
        if isinstance(value, (dict, list)):
            if id(value) in ancestors:
                raise ValueError("YAML_CYCLE")
            ancestors.add(id(value))
            if isinstance(value, dict):
                keys = [str(key) for key in value]
                if len(set(keys)) != len(keys):
                    raise ValueError("NORMALIZED_KEY_COLLISION")
                result: Any = {str(key): convert(item) for key, item in value.items()}
            else:
                result = [convert(item) for item in value]
            ancestors.remove(id(value))
            return result
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("NONFINITE_INPUT")
        if value is not None and not isinstance(value, (str, bool, int, float)):
            raise ValueError("NON_JSON_SCALAR")
        return value

    result = convert(parsed)
    if not isinstance(result, dict):
        raise ValueError("SPEC_OBJECT_REQUIRED")
    return result


def environment() -> dict[str, Any]:
    node = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10, check=False)
    return {
        "python": sys.version,
        "pythonExecutable": sys.executable,
        "node": node.stdout.strip(),
        "nodeVersionExit": node.returncode,
        "platform": platform.platform(),
        "pyyaml": yaml.__version__,
        "timeZone": "UTC for evidence timestamps",
        "monetaryCost": None,
    }


def acquire(root: Path, protocol: dict[str, Any], phase: str, guard: Callable[[], Any]) -> dict[str, Any]:
    started, cpu, child = time.perf_counter(), time.process_time(), children_cpu()
    folder = root / "inputs/acquired"
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {
            "schema": "public-moby-inputs/v1",
            "createdAt": now(),
            "entries": {},
            "attemptsPerArtifact": 1,
            "normalization": "Safe YAML, timestamp strings preserved, all mapping keys converted to strings with collision rejection; finite JSON only",
            "actualCompleteMonetaryCost": None,
            "actualHumanSeconds": None,
            "sessions": [],
        }
    )
    versions = sorted({version for pair in selected_pairs(protocol, phase) for version in pair})
    previous = json.loads((root / "discovery/acquisition.json").read_text())
    reused = {row["path"]: row for row in previous if row.get("status") == "ok"}
    for version in versions:
        if version in manifest["entries"]:
            continue
        if (
            not version.startswith("v")
            or len(version.split(".")) != 3
            or not all(part.isdigit() for part in version[1:].split("."))
        ):
            raise ValueError("UNDECLARED_VERSION_FORMAT")
        entry: dict[str, Any] = {"version": version, "status": "ATTEMPTING", "startedAt": now(), "artifacts": {}}
        manifest["entries"][version] = entry
        save(manifest_path, manifest)
        entry_start, entry_cpu, entry_child = time.perf_counter(), time.process_time(), children_cpu()
        try:
            for kind, remote, extension in [
                ("spec", protocol["source_path"], "yaml"),
                ("license", "LICENSE", "LICENSE"),
            ]:
                url = (
                    "https://raw.githubusercontent.com/" + protocol["source_repository"] + "/" + version + "/" + remote
                )
                destination = folder / (version + "." + extension)
                existing = "inputs/discovery-docker-" + version + ".yaml" if kind == "spec" else "heritage/moby-LICENSE"
                use_existing = existing in reused and (
                    kind == "spec" and version in {"v25.0.0", "v26.0.0"} or kind == "license" and version == "v26.0.0"
                )
                acquisition_start, acquisition_cpu = time.perf_counter(), time.process_time()
                artifact: dict[str, Any] = {
                    "url": url,
                    "status": "ATTEMPTING",
                    "attempts": 0 if use_existing else 1,
                    "reusedDiscoveryInput": use_existing,
                    "path": str(destination.relative_to(root)),
                }
                entry["artifacts"][kind] = artifact
                save(manifest_path, manifest)
                guard()
                if use_existing:
                    raw = (root / existing).read_bytes()
                    if len(raw) != reused[existing]["bytes"] or sha(raw) != reused[existing]["sha256"]:
                        raise ValueError("DISCOVERY_INPUT_CUSTODY:" + existing)
                    artifact["originalPath"] = existing
                    artifact["originalHistoricalRetrievalChargedAgain"] = False
                else:
                    with urllib.request.urlopen(url, timeout=45) as response:
                        raw = response.read(10_000_001)
                        artifact["httpStatus"] = response.status
                    if len(raw) > 10_000_000:
                        raise ValueError("INPUT_SIZE_BOUND")
                destination.write_bytes(raw)
                artifact.update(
                    {
                        "status": "ACQUIRED",
                        "bytes": len(raw),
                        "sha256": sha(raw),
                        "wallSeconds": time.perf_counter() - acquisition_start,
                        "cpuSeconds": time.process_time() - acquisition_cpu,
                    }
                )
                save(manifest_path, manifest)
            normalize_start, normalize_cpu = time.perf_counter(), time.process_time()
            original = (folder / (version + ".yaml")).read_bytes()
            document = normalized_yaml(original)
            data = (json.dumps(document, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
            output = folder / (version + ".json")
            output.write_bytes(data)
            entry["normalized"] = {
                "path": str(output.relative_to(root)),
                "bytes": len(data),
                "sha256": sha(data),
                "wallSeconds": time.perf_counter() - normalize_start,
                "cpuSeconds": time.process_time() - normalize_cpu,
            }
            entry["status"] = "ACQUIRED"
        except Exception as error:
            entry.update(
                {"status": "FAILED", "errorType": type(error).__name__, "error": str(error), "replacement": None}
            )
        entry.update(
            {
                "finishedAt": now(),
                "wallSeconds": time.perf_counter() - entry_start,
                "cpuSeconds": time.process_time() - entry_cpu + children_cpu() - entry_child,
            }
        )
        save(manifest_path, manifest)
    session = {
        "phase": phase,
        "finishedAt": now(),
        "versions": versions,
        "wallSeconds": time.perf_counter() - started,
        "cpuSeconds": time.process_time() - cpu + children_cpu() - child,
        "runtime": environment(),
    }
    manifest["sessions"].append(session)
    save(manifest_path, manifest)
    return {
        "manifest": str(manifest_path),
        "sha256": sha(manifest_path.read_bytes()),
        "session": session,
        "statuses": {version: manifest["entries"][version]["status"] for version in versions},
    }


def run_process(
    command: list[str], directory: Path, prefix: Path, guard: Callable[[], Any], timeout: float = 60
) -> dict[str, Any]:
    if not 0 < timeout <= 60:
        raise ValueError("PROCESS_BOUND")
    record: dict[str, Any] = {
        "command": command,
        "cwd": str(directory),
        "startedAt": now(),
        "executed": False,
        "stdout": prefix.name + ".stdout",
        "stderr": prefix.name + ".stderr",
        "timeoutSeconds": timeout,
    }
    start = time.perf_counter()
    with prefix.with_suffix(".stdout").open("wb") as stdout, prefix.with_suffix(".stderr").open("wb") as stderr:
        guard()
        try:
            process = subprocess.Popen(command, cwd=directory, stdout=stdout, stderr=stderr, start_new_session=True)
        except OSError as error:
            record.update(
                {
                    "exit": None,
                    "timedOut": False,
                    "wallSeconds": time.perf_counter() - start,
                    "processWallSeconds": 0,
                    "cpuSeconds": 0,
                    "maxRssKiB": None,
                    "errorType": type(error).__name__,
                    "error": str(error),
                    "finishedAt": now(),
                }
            )
            return record
        record["executed"] = True
        execution_start = time.perf_counter()
        timed_out = False
        while True:
            completed, status, usage = os.wait4(process.pid, os.WNOHANG)
            if completed:
                break
            if time.perf_counter() - execution_start >= timeout:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                _, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(0.005)
        process.returncode = os.waitstatus_to_exitcode(status)
    record.update(
        {
            "exit": process.returncode,
            "timedOut": timed_out,
            "wallSeconds": time.perf_counter() - start,
            "processWallSeconds": time.perf_counter() - execution_start,
            "cpuSeconds": usage.ru_utime + usage.ru_stime,
            "maxRssKiB": usage.ru_maxrss,
            "finishedAt": now(),
            "cpuIncludesWaitedDescendants": True,
            "maxRssMeaning": "Linux maximum resident set reported for this process tree; not summed concurrent RSS",
        }
    )
    return record


def check_inputs(
    root: Path, manifest_path: Path, manifest_hash: str, entries: dict[str, Any], versions: list[str]
) -> None:
    if sha(manifest_path.read_bytes()) != manifest_hash:
        raise ValueError("INPUT_MANIFEST_CHANGED")
    for version in versions:
        entry = entries[version]
        if entry["status"] != "ACQUIRED":
            raise ValueError("INPUT_ACQUISITION_FAILED:" + version)
        for record in [*entry["artifacts"].values(), entry["normalized"]]:
            data = (root / record["path"]).read_bytes()
            if len(data) != record["bytes"] or sha(data) != record["sha256"]:
                raise ValueError("INPUT_CUSTODY_FAILED:" + version)


def package_conventional(directory: Path, expected: list[str], source: Path) -> dict[str, Any]:
    output = directory / "dossier.json"
    report = json.loads(output.read_text())
    measured = json.loads((directory / "dossier.measurement.json").read_text())
    if [measured["before_sha256"], measured["after_sha256"]] != expected or measured["output_sha256"] != sha(
        output.read_bytes()
    ):
        raise ValueError("CONVENTIONAL_INPUT_OUTPUT_BINDING")
    if measured["source_sha256"] != sha(source.read_bytes()):
        raise ValueError("CONVENTIONAL_SOURCE_BINDING")
    decision = {
        "en": "Review every listed response-schema change before upgrading affected clients.",
        "fr": "Examiner chaque modification de schéma avant de migrer les clients concernés.",
        "changes": report["changes"],
        "unassessed": report["unassessed"],
        "limits": report["limitations"],
        "actualCustomerAcceptance": False,
        "actualHumanSeconds": None,
        "actualMonetaryCost": None,
        "authority": [],
        "settlement": "NOT_CONNECTED",
    }
    save(directory / "upgrade-review-en-fr.json", decision)
    text = (
        "# API response upgrade review / Examen de migration API\n\n"
        + decision["en"]
        + "\n\n"
        + decision["fr"]
        + "\n\n"
    )
    text += f"Changed surfaces / Structures modifiées: {len(report['changes'])}.\n\n"
    text += "The complete source-bound dossier and independent acceptance receipt accompany this outcome.\n\n"
    text += "Le dossier complet et son contrôle indépendant accompagnent ce résultat.\n\n"
    text += "No live server, paying customer, real settlement or production authority is established.\n"
    (directory / "upgrade-review.md").write_text(text)
    return {"changedSurfaces": len(report["changes"]), "unassessed": report["unassessed"]}


def campaign(
    root: Path, protocol: dict[str, Any], phase: str, output: Path, guard: Callable[[], Any]
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    start, cpu, child = time.perf_counter(), time.process_time(), children_cpu()
    manifest_path = root / "inputs/acquired/manifest.json"
    manifest_raw = manifest_path.read_bytes()
    manifest_hash, inputs = sha(manifest_raw), json.loads(manifest_raw)
    pairs = selected_pairs(protocol, phase)
    versions_all = Counter(version for pair in selected_pairs(protocol, "all") for version in pair)
    result: dict[str, Any] = {
        "schema": "api-production-campaign/v1",
        "phase": phase,
        "startedAt": now(),
        "inputManifestSha256": manifest_hash,
        "sourceQualification": "PENDING",
        "records": [],
        "runtime": environment(),
        "actualCollectionsUsd": 0,
        "actualCompleteMonetaryCost": None,
        "actualHumanSeconds": None,
        "claimScope": "Source-qualified bounded research outputs, not customer or live-service acceptance",
    }
    stopped = False
    for index, pair in enumerate(pairs):
        order = list("ABCD")
        rotation = index % 4
        order = order[rotation:] + order[:rotation]
        for arm in order:
            name = f"{phase}-{index + 1:02d}-{pair[0]}-to-{pair[1]}-{arm}"
            directory = output / name
            directory.mkdir()
            record: dict[str, Any] = {
                "id": name,
                "arm": arm,
                "pair": pair,
                "order": order.index(arm),
                "accepted": False,
                "status": "NOT_RUN",
                "processes": [],
                "actualHumanSeconds": None,
                "actualCompleteMonetaryCost": None,
            }
            job_start, job_cpu, job_child = time.perf_counter(), time.process_time(), children_cpu()
            try:
                if stopped:
                    record["status"] = "NOT_RUN_SOURCE_CUSTODY_HOLD"
                    continue
                if any(inputs["entries"].get(version, {}).get("status") != "ACQUIRED" for version in pair):
                    record["status"] = "INPUT_ACQUISITION_FAILED"
                    continue
                old, new = [root / inputs["entries"][version]["normalized"]["path"] for version in pair]
                service = directory / "service"

                def operation_guard() -> None:
                    guard()
                    check_inputs(root, manifest_path, manifest_hash, inputs["entries"], pair)

                if arm == "A":
                    command = [
                        sys.executable,
                        str(root / "comparators/conventional/conventional.py"),
                        str(old),
                        str(new),
                        str(service / "dossier.json"),
                    ]
                else:
                    command = [
                        "node",
                        str(root / "src/run_service.mjs"),
                        str(old),
                        str(new),
                        str(service),
                        ARM_MODES[arm],
                    ]
                production = run_process(command, root, directory / "production", operation_guard)
                record["processes"].append(production)
                if production["exit"] != 0:
                    record["status"] = "PRODUCTION_TIMEOUT" if production["timedOut"] else "PRODUCTION_FAILED"
                    continue
                if arm == "A":
                    verifier = [
                        sys.executable,
                        str(root / "comparators/conventional/verify_dossier.py"),
                        str(old),
                        str(new),
                        str(service / "dossier.json"),
                    ]
                else:
                    verifier = [
                        sys.executable,
                        str(root / "tests/accept_dossier.py"),
                        str(old),
                        str(new),
                        str(service),
                        "--receipt",
                        str(service / "independent-acceptance.json"),
                    ]
                verification = run_process(verifier, root, directory / "verification", operation_guard)
                record["processes"].append(verification)
                if verification["exit"] != 0:
                    record["status"] = "ACCEPTANCE_TIMEOUT" if verification["timedOut"] else "ACCEPTANCE_FAILED"
                    continue
                verdict = json.loads((directory / "verification.stdout").read_text())
                if verdict.get("accepted") is not True:
                    raise ValueError("ACCEPTANCE_VERDICT")
                if arm == "A":
                    record["summary"] = package_conventional(
                        service,
                        [sha(old.read_bytes()), sha(new.read_bytes())],
                        root / "comparators/conventional/conventional.py",
                    )
                    save(service / "independent-acceptance.json", verdict)
                else:
                    measured = json.loads((service / "measurement.json").read_text())
                    scope = measured["scope"]
                    if (
                        scope["authority"] != []
                        or scope["admission"] != "HOLD"
                        or scope["settlement"] != "NOT_CONNECTED"
                    ):
                        raise ValueError("UNEXPECTED_EXECUTION_AUTHORITY")
                    record["summary"] = measured["summary"]
                record.update({"accepted": True, "status": "ACCEPTED_SCOPED_RESEARCH_OUTPUT", "acceptance": verdict})
            except Exception as error:
                record.update(
                    {
                        "status": (
                            "SOURCE_CUSTODY_FAILED"
                            if "SOURCE_" in str(error)
                            else (
                                "INPUT_CUSTODY_FAILED"
                                if "CUSTODY" in str(error) or "MANIFEST_CHANGED" in str(error)
                                else "DRIVER_OR_OUTPUT_FAILED"
                            )
                        ),
                        "errorType": type(error).__name__,
                        "error": str(error),
                    }
                )
                if record["status"] in {"SOURCE_CUSTODY_FAILED", "INPUT_CUSTODY_FAILED"}:
                    stopped = True
            finally:
                record.update(
                    {
                        "wallSeconds": time.perf_counter() - job_start,
                        "cpuSeconds": time.process_time() - job_cpu + children_cpu() - job_child,
                        "maxProcessRssKiB": max(
                            [
                                process["maxRssKiB"]
                                for process in record["processes"]
                                if process["maxRssKiB"] is not None
                            ],
                            default=None,
                        ),
                        "cpuAccounting": "outer driver self CPU plus waited-child CPU delta once; internal timing receipts are not added",
                        "sharedAcquisitionCpuSeconds": sum(
                            inputs["entries"].get(version, {}).get("cpuSeconds", 0) / (versions_all[version] * 4)
                            for version in pair
                        ),
                        "sharedAcquisitionWallSeconds": sum(
                            inputs["entries"].get(version, {}).get("wallSeconds", 0) / (versions_all[version] * 4)
                            for version in pair
                        ),
                        "finishedAt": now(),
                    }
                )
                save(directory / "record.json", record)
                result["records"].append(record)
                save(output / "campaign.json", result)
    try:
        result["finalSourceCheck"] = guard()
        if sha(manifest_path.read_bytes()) != manifest_hash:
            raise ValueError("INPUT_MANIFEST_CHANGED")
        result["sourceQualification"] = "PASS" if not stopped else "HOLD"
    except Exception as error:
        result.update({"sourceQualification": "HOLD", "finalSourceError": str(error)})
    result.update(
        {
            "finishedAt": now(),
            "wallSeconds": time.perf_counter() - start,
            "cpuSeconds": time.process_time() - cpu + children_cpu() - child,
        }
    )
    result["driverOverheadCpuSeconds"] = result["cpuSeconds"] - sum(
        record["cpuSeconds"] for record in result["records"]
    )
    calibration: dict[str, Any] = {
        "phase": phase,
        "sourceQualification": result["sourceQualification"],
        "arms": {},
        "allMoneyIsAssumed": True,
        "actualCompleteMonetaryCost": None,
        "actualHumanSeconds": None,
        "sharedAllocation": "each version acquisition/normalization once, divided among its appearances in the eight registered questions and four arms; transfer shares remain explicit until executed",
        "verificationIncluded": True,
        "failedOutputsCharged": True,
    }
    for arm in "ABCD":
        records = [record for record in result["records"] if record["arm"] == arm]
        accepted = sum(record["accepted"] for record in records)
        calibration["arms"][arm] = {
            "cases": len(records),
            "accepted": sum(record["accepted"] for record in records),
            "totalCpuSecondsIncludingFailures": sum(record["cpuSeconds"] for record in records),
            "cpuSecondsPerAcceptedIncludingFailures": (
                sum(record["cpuSeconds"] for record in records) / accepted if accepted else None
            ),
            "meanCpuSeconds": sum(record["cpuSeconds"] for record in records) / len(records),
            "meanWallSeconds": sum(record["wallSeconds"] for record in records) / len(records),
            "meanSharedAcquisitionCpuSeconds": sum(record["sharedAcquisitionCpuSeconds"] for record in records)
            / len(records),
            "perCase": [
                {
                    key: record[key]
                    for key in [
                        "id",
                        "pair",
                        "accepted",
                        "status",
                        "cpuSeconds",
                        "wallSeconds",
                        "sharedAcquisitionCpuSeconds",
                    ]
                }
                for record in records
            ],
        }
    save(output / "campaign.json", result)
    save(output / "calibration.json", calibration)
    return calibration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["acquire", "run"])
    parser.add_argument("--phase", choices=["primary", "transfer", "all"], default="primary")
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--freeze-sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    protocol = json.loads((STUDY / "protocol/production.json").read_text())

    def guard() -> dict[str, Any]:
        return verify_freeze(STUDY, args.freeze, args.freeze_sha256)

    if args.action == "acquire":
        guard()
        result = acquire(STUDY, protocol, args.phase, guard)
    else:
        if args.output is None:
            parser.error("--output is required for run")
        result = campaign(STUDY, protocol, args.phase, args.output, guard)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_SHA256 = "583bc6d7cb5736d6805ceb87407fcf1b3c234de813aad1fba38270d875cfb586"
JOB_FIELDS = {
    "schema", "id", "lock_path", "lock_sha256", "pyproject_path", "pyproject_sha256",
    "project_extras", "wheelhouse_path", "wheels", "target_environment",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_FIELD:" + key)
        out[key] = value
    return out


def read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > 10_000_000:
        raise ValueError("JSON_BYTE_BOUND")
    out = json.loads(raw, object_pairs_hook=unique_pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
    if not isinstance(out, dict):
        raise ValueError("OBJECT_REQUIRED")
    return out


def in_study(path: Path, *, must_exist: bool = True) -> Path:
    absolute = Path(path).absolute()
    resolved = absolute.resolve()
    if not resolved.is_relative_to(ROOT) or resolved == ROOT:
        raise ValueError("STUDY_PATH_REQUIRED")
    cursor = absolute
    while cursor != cursor.parent:
        if cursor.is_symlink():
            raise ValueError("SYMLINK_NOT_SUPPORTED")
        if cursor == ROOT:
            break
        cursor = cursor.parent
    if must_exist and not resolved.exists():
        raise ValueError("INPUT_ABSENT")
    return resolved


def verifier() -> Any:
    path = ROOT / "production/verify.py"
    if sha256(path) != VERIFIER_SHA256:
        raise ValueError("INHERITED_VERIFIER_CHANGED")
    spec = importlib.util.spec_from_file_location("agi_alpha_inherited_metadata_verifier", path)
    if spec is None or spec.loader is None:
        raise ValueError("VERIFIER_IMPORT_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_job(job_path: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    job_path = in_study(job_path)
    if not job_path.is_file():
        raise ValueError("JOB_REGULAR_FILE_REQUIRED")
    job = read_json(job_path)
    if set(job) != JOB_FIELDS or job.get("schema") != "agialpha-lock-job/v1":
        raise ValueError("JOB_SCHEMA")
    if not isinstance(job["id"], str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,160}", job["id"]):
        raise ValueError("JOB_ID")
    if job["target_environment"] != default_environment():
        raise ValueError("EXACT_CURRENT_ENVIRONMENT_REQUIRED")
    paths = {}
    for key in ("lock_path", "pyproject_path", "wheelhouse_path"):
        value = job[key]
        if not isinstance(value, str) or not value or Path(value).is_absolute():
            raise ValueError("RELATIVE_INPUT_REQUIRED")
        paths[key] = in_study(job_path.parent / value)
    for key, hash_key in (("lock_path", "lock_sha256"), ("pyproject_path", "pyproject_sha256")):
        if not paths[key].is_file() or sha256(paths[key]) != job[hash_key]:
            raise ValueError("INPUT_IDENTITY:" + key)
    if not paths["wheelhouse_path"].is_dir():
        raise ValueError("WHEELHOUSE_DIRECTORY_REQUIRED")
    extras = job["project_extras"]
    if not isinstance(extras, list) or any(not isinstance(x, str) for x in extras) or len(extras) != len(set(extras)):
        raise ValueError("PROJECT_EXTRAS")
    project = tomllib.loads(paths["pyproject_path"].read_text())["project"]
    if any(x not in project.get("optional-dependencies", {}) for x in extras):
        raise ValueError("UNKNOWN_PROJECT_EXTRA")
    wheels = job["wheels"]
    if not isinstance(wheels, list) or not 1 <= len(wheels) <= 500:
        raise ValueError("WHEEL_BOUND")
    seen = set()
    for wheel in wheels:
        if not isinstance(wheel, dict) or set(wheel) != {"filename", "name", "version", "sha256"}:
            raise ValueError("WHEEL_FIELDS")
        if any(not isinstance(wheel[k], str) for k in wheel):
            raise ValueError("WHEEL_TYPES")
        filename = wheel["filename"]
        if Path(filename).name != filename or "/" in filename or "\\" in filename or not filename.endswith(".whl"):
            raise ValueError("WHEEL_BASENAME")
        name = canonicalize_name(wheel["name"])
        if name in seen or not re.fullmatch("[a-f0-9]{64}", wheel["sha256"]):
            raise ValueError("WHEEL_IDENTITY")
        seen.add(name)
        path = in_study(paths["wheelhouse_path"] / filename)
        if not path.is_file():
            raise ValueError("WHEEL_ABSENT")
    return job, paths


def mission_key(job_path: Path) -> str:
    job, paths = validate_job(job_path)
    checker = verifier()
    lock = checker.parse_lock(paths["lock_path"].read_bytes(), job["target_environment"])
    project = tomllib.loads(paths["pyproject_path"].read_text())["project"]
    roots = list(project.get("dependencies", []))
    for extra in job["project_extras"]:
        roots += project["optional-dependencies"][extra]
    identity = {
        "schema": "verified-capability-underlying-mission/v1",
        "lock": sorted((name, str(row["requirement"]), sorted(row["hashes"])) for name, row in lock.items()),
        "roots": sorted(str(Requirement(text)) for text in roots),
        "requires_python": project.get("requires-python", ""),
        "project_extras": sorted(job["project_extras"]),
        "wheels": sorted((canonicalize_name(w["name"]), w["version"], w["sha256"]) for w in job["wheels"]),
        "target_environment": job["target_environment"],
    }
    return hashlib.sha256(canonical(identity)).hexdigest()


def reverify(job_path: Path, result_path: Path) -> dict[str, Any]:
    try:
        validate_job(job_path)
        in_study(result_path)
        for path in result_path.parent.rglob("*"):
            if path.is_symlink():
                raise ValueError("RESULT_SYMLINK")
        return verifier().verify(job_path, result_path)
    except (ValueError, TypeError, KeyError, OSError) as error:
        return {"schema": "agialpha-independent-lock-certificate/v1", "status": "INCOMPLETE",
                "verdict": "INCOMPLETE", "errors": [type(error).__name__ + ": " + str(error)],
                "application_qualified": False, "authority": [], "financial_action": False}


def check_completed_packet(job_path: Path, directory: Path, *, native: bool) -> dict[str, Any]:
    job, _ = validate_job(job_path)
    directory = in_study(directory)
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("RESULT_SYMLINK")
    result_path = directory / "delivery/result.json"
    certificate_path = directory / "verification.json"
    result, certificate = read_json(result_path), read_json(certificate_path)
    for record in (result, certificate):
        if record.get("job_sha256") != sha256(job_path) or record.get("job_id") != job["id"]:
            raise ValueError("OUTPUT_JOB_BINDING")
        if record.get("application_qualified") is not False or record.get("authority") != []:
            raise ValueError("UNSUPPORTED_AUTHORITY")
        if record.get("financial_action") is not False:
            raise ValueError("UNSUPPORTED_FINANCIAL_ACTION")
    if certificate.get("result_sha256") != sha256(result_path):
        raise ValueError("CERTIFICATE_RESULT_BINDING")
    if certificate.get("verifier", {}).get("source_sha256") != VERIFIER_SHA256:
        raise ValueError("CERTIFICATE_VERIFIER_BINDING")
    complete = certificate.get("status") == "COMPLETE"
    verdict = certificate.get("verdict") if complete else "INCOMPLETE"
    if complete and (verdict not in {"CONSISTENT", "CONFLICT"} or result.get("decision") != verdict):
        raise ValueError("DECISION_DISAGREEMENT")
    for key in ("stdout", "stderr", "report"):
        name = result.get("files", {}).get(key)
        if name is None and key == "report":
            continue
        if not isinstance(name, str) or Path(name).is_absolute():
            raise ValueError("ARTIFACT_PATH")
        artifact = in_study(result_path.parent / name)
        if not artifact.is_relative_to(result_path.parent) or not artifact.is_file():
            raise ValueError("ARTIFACT_OUTSIDE_PACKET")
        evidence_key = "pip_report_sha256" if key == "report" else key + "_sha256"
        expected = certificate.get("evidence", {}).get(evidence_key)
        if expected is not None and expected != sha256(artifact):
            raise ValueError("CAPTURE_CHANGED_AFTER_VERIFICATION")
    if native:
        pack, inspection = read_json(directory / "pack.json"), read_json(directory / "inspection.json")
        if pack.get("schema") != "successor-workbench/v1" or pack["result"]["decision"] != verdict:
            raise ValueError("NATIVE_RESULT_BINDING")
        evidence = pack["result"]["evidence"]
        if evidence.get("jobSha256") != sha256(job_path) or evidence.get("verificationSha256") != sha256(certificate_path):
            raise ValueError("NATIVE_EVIDENCE_BINDING")
        if pack.get("evaluation", {}).get("admission") != "HOLD" or pack["evaluation"].get("authority") != []:
            raise ValueError("NATIVE_ADMISSION_CHANGED")
        if inspection.get("activeProof") != [] or inspection.get("activeAuthority") != []:
            raise ValueError("HISTORICAL_IMPORT_CANNOT_GRANT_AUTHORITY")
    return {"accepted": complete, "decision": verdict, "job_id": job["id"],
            "mission_key": mission_key(job_path), "certificate": certificate, "result": result,
            "application_qualified": False, "authority": [], "financial_action": False}

# SPDX-License-Identifier: Apache-2.0
"""Retired legacy orchestration and the shared Docker boundary for new ASTs.

The legacy protocol does not authenticate source field/span associations. Its
run/resume/reproduce entry points fail closed; the current critic loop retains
the isolation helper and driver without using the retired admission protocol.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any, cast

from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable, secure_run

from ..structural_transfer.contracts import digest, read, write_new
from . import specification as spec

LEGACY_QUALIFICATION_RETIRED = (
    "Legacy specification qualification is retired: its protocol does not bind source fields/spans. "
    "Use alpha-agent invention critic-loop with --context and a freshly frozen critic verifier. "
    "critic-resume accepts only critic-loop checkpoints; legacy checkpoints remain unqualified historical evidence."
)


def reject_legacy_qualification() -> None:
    """Refuse the ungrounded protocol before reading, writing or executing work."""
    raise ValueError(LEGACY_QUALIFICATION_RETIRED)


DRIVER = """import json,sys
p=json.load(open(sys.argv[1]))
units={"V":"voltage","kV":"voltage","VA":"apparent_power","kVA":"apparent_power","MVA":"apparent_power","Hz":"frequency"}
outputs=[]
trace=[]
steps=0
def visit(node,record,observed):
 global steps
 steps+=1
 if steps>16384: raise ValueError("operation budget")
 op=node["op"]
 trace.append({"record":record["id"],"op":op})
 if op=="observe":
  observed[node["field"]]=record["fields"].get(node["field"])
 elif op=="emit": return node["status"]
 elif op=="sequence":
  for child in node["steps"]:
   out=visit(child,record,observed)
   if out is not None: return out
 elif op=="if":
  t=node["test"]; value=observed[t["field"]]
  yes=value is not None and units.get(value["unit"])==t["dimension"]
  return visit(node["then"] if yes else node["else"],record,observed)
 else: raise ValueError("uninstalled operator")
for record in p["records"]:
 result=visit(p["program"],record,{})
 if result not in ["CONSISTENT","ABSTAIN"]: raise ValueError("missing disposition")
 outputs.append({"id":record["id"],"status":result})
print(json.dumps({"outputs":outputs,"trace":trace,"operations":steps},sort_keys=True))
"""


def source_hashes() -> dict[str, str]:
    """Bind trusted implementation, specification and existing isolation code."""
    root = Path(__file__).resolve().parents[3]
    relative = [
        "core/runtime/invention_automation/specification.py",
        "core/runtime/invention_automation/specification_run.py",
        "core/runtime/invention_automation/operator.py",
        "core/runtime/structural_transfer/contracts.py",
        "core/utils/secure_run.py",
    ]
    return {"alpha_factory_v1/" + name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in relative}


def isolated(program: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Run only through secure_run, with a locally present digest-pinned image.

    No daemon, mutable image, missing image or isolation error permits a host
    fallback. No image acquisition is attempted. This adds an admission condition
    without changing existing security configuration or secure_run behavior.
    """
    if not shutil.which("docker"):
        try:
            secure_run([sys.executable, "-c", "pass"])
        except SandboxUnavailable as error:
            return {"status": "BLOCKED", "executed": False, "reason": str(error)}
        raise RuntimeError("isolation inventory changed; restart admission")
    image = os.getenv("ALPHA_SANDBOX_IMAGE", "")
    if not re.fullmatch(r"[A-Za-z0-9./:_-]+@sha256:[a-f0-9]{64}", image):
        return {
            "status": "BLOCKED",
            "executed": False,
            "reason": "locally provisioned digest-pinned sandbox image required",
        }
    probe = subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=5, check=False)
    if probe.returncode:
        return {"status": "BLOCKED", "executed": False, "reason": "pinned image absent; downloads are not authorized"}
    with tempfile.TemporaryDirectory(prefix="alpha-specification-") as name:
        temp = Path(name)
        script = temp / "driver.py"
        payload = temp / "payload.json"
        script.write_text(DRIVER)
        payload.write_text(json.dumps({"program": program, "records": records}))
        try:
            result = secure_run([sys.executable, str(script), str(payload)])
        except SandboxUnavailable as error:
            return {"status": "BLOCKED", "executed": False, "reason": str(error)}
        if result.returncode:
            return {
                "status": "FAILED",
                "executed": True,
                "reason": result.stderr[:1000],
                "stdout": result.stdout,
                "returncode": result.returncode,
            }
        return {
            "status": "EXECUTED_UNVERIFIED",
            "executed": True,
            "image": image,
            "artifact": json.loads(result.stdout),
        }


def independent_criticism(request_path: Path, witness_path: Path, freeze: Path) -> dict[str, Any]:
    """Replay the historical unqualified source-wide checker, never current admission.

    This helper preserves the old engineering protocol for investigation. Its
    literal occurrence check cannot establish source field/span attribution.
    Native generation, resume and replay under that protocol are retired.
    """
    root = Path(__file__).resolve().parents[4]
    command = [
        sys.executable,
        "-B",
        "-m",
        "contrib.invention_automation.qualify_verify",
        "--root",
        str(root),
        "--freeze",
        str(freeze.resolve()),
        "--request",
        str(request_path.resolve()),
        "--criticism-only",
        "--witness",
        str(witness_path.resolve()),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
        env={"PATH": os.defpath, "LANG": "C.UTF-8", "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        raise ValueError("independent criticism rejected or unavailable: " + result.stderr[-2000:])
    receipt = json.loads(result.stdout)
    if receipt.get("critic_validated") is not True or receipt.get("confirmation") is not False:
        raise ValueError("independent criticism receipt invalid")
    return cast(dict[str, Any], receipt)


def run(request: dict[str, Any], output: Path, *, freeze: Path) -> dict[str, Any]:
    """Refuse current admission through the retired legacy protocol."""
    reject_legacy_qualification()
    existed = output.exists()
    start_cpu, start_wall = time.process_time_ns(), time.monotonic_ns()
    try:
        return _run(request, output, freeze=freeze)
    except Exception as error:
        if not existed and output.is_dir() and not output.is_symlink():
            write_new(
                output / "failure.json",
                {
                    "type": type(error).__name__,
                    "reason": str(error),
                    "self_cpu_ns": time.process_time_ns() - start_cpu,
                    "wall_ns": time.monotonic_ns() - start_wall,
                    "scope": "retained failed attempt; never retry with a reset allocation",
                },
            )
        raise


def _run(request: dict[str, Any], output: Path, *, freeze: Path) -> dict[str, Any]:
    """Keep the historical implementation inert, including direct internal calls."""
    reject_legacy_qualification()
    spec.validate_request(request)
    if any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError("symlink output refused")
    if shutil.disk_usage(output.parent).free < 2 * 1024**3:
        raise ValueError("preserve original minimum 2 GiB free")
    now = datetime.now(UTC)
    # Inherit the existing deadline; never create a fresh eight-hour campaign.
    if now >= datetime(2026, 10, 29, 16, 53, tzinfo=UTC):
        raise ValueError("inherited generation cutoff reached; verification and read-only resume remain available")
    output.mkdir(parents=False, exist_ok=False)
    write_new(output / "request.json", request)
    initial_cpu, initial_wall = time.process_time_ns(), time.monotonic_ns()
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    witness = spec.criticize(request)
    write_new(output / "criticism.json", witness)
    receipt = independent_criticism(output / "request.json", output / "criticism.json", freeze)
    write_new(output / "criticism-verification.json", receipt)
    constraint = spec.constrain(request, witness)
    construction = spec.construct(request, constraint)
    sandbox = isolated(construction["program"], request["records"])
    child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    resources = {
        "self_cpu_ns": time.process_time_ns() - initial_cpu,
        "wall_ns": time.monotonic_ns() - initial_wall,
        "child_cpu_seconds": str(
            (child_end.ru_utime + child_end.ru_stime) - (child_start.ru_utime + child_start.ru_stime)
        ),
        "model_tokens": "UNKNOWN",
        "prior_campaign_consumption": "UNKNOWN; not zero",
        "deterministic_candidate_count": sum(
            a["origin"] == "deterministic-constraint-compiler" for a in construction["attempts"]
        ),
    }
    result = {
        "schema": "agialpha/specification-synthesis-bundle/v1",
        "request_hash": digest(request),
        "baseline_hash": digest(request["baseline"]),
        "proposal_hash": digest(request["proposal"]),
        "criticism": witness,
        "constraint": constraint,
        "program": construction["program"],
        "construction": construction,
        "static": construction["static"],
        "sandbox": sandbox,
        "conventional_reference": spec.inspect_records(request),
        "source_hashes": source_hashes(),
        "economics": {
            "status": "UNKNOWN",
            "operating_cohort_admitted": False,
            "earned_surplus": "0",
            "actual_external_cash_paid": "0",
        },
        "resources": resources,
        "confirmation": False,
    }
    write_new(output / "bundle.json", result)
    write_new(
        output / "experience.json",
        {
            "schema": "agialpha/specification-experience/v1",
            "parent": None,
            "request_hash": digest(request),
            "source_hashes": source_hashes(),
            "witness": witness,
            "constraint": constraint,
            "program": construction["program"],
            "costs": resources,
            "promotion": "STATIC_ONLY; NOT DEPLOYABLE",
            "limits": [
                "one exposed source witness",
                "no physical suitability",
                "no commercial admission",
                "generated execution unverified",
                "no demonstrated learning benefit",
            ],
        },
    )
    write_new(
        output / "checkpoint.json",
        {
            "schema": "agialpha/specification-checkpoint/v1",
            "files": {
                name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                for name in [
                    "request.json",
                    "bundle.json",
                    "experience.json",
                    "criticism.json",
                    "criticism-verification.json",
                ]
            },
        },
    )
    return result


def resume(request: dict[str, Any], output: Path) -> dict[str, Any]:
    """Refuse promotion of an old checkpoint through the retired protocol."""
    reject_legacy_qualification()
    if any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError("symlink checkpoint refused")
    checkpoint = read(output / "checkpoint.json")
    if set(checkpoint) != {"schema", "files"} or checkpoint["schema"] != "agialpha/specification-checkpoint/v1":
        raise ValueError("checkpoint schema")
    if set(checkpoint["files"]) != {
        "request.json",
        "bundle.json",
        "experience.json",
        "criticism.json",
        "criticism-verification.json",
    }:
        raise ValueError("checkpoint file set")
    for name, expected in checkpoint["files"].items():
        path = output / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError("checkpoint corruption: " + name)
    original, result = read(output / "request.json"), read(output / "bundle.json")
    if digest(original) != digest(request) or result["request_hash"] != digest(request):
        raise ValueError("resume input identity mismatch")
    if result["source_hashes"] != source_hashes():
        raise ValueError("resume source mismatch; preserve old run and qualify a new revision")
    return cast(dict[str, Any], result)


def reproduce(request: dict[str, Any], source: Path, output: Path) -> dict[str, Any]:
    """Refuse relabeling old evidence as current qualification or confirmation."""
    reject_legacy_qualification()
    result = resume(request, source)
    if any(p.is_symlink() for p in [output, *output.parents]):
        raise ValueError("symlink replay refused")
    if shutil.disk_usage(output.parent).free < 2 * 1024**3:
        raise ValueError("preserve original minimum 2 GiB free")
    output.mkdir(exist_ok=False)
    for name in [*read(source / "checkpoint.json")["files"], "checkpoint.json"]:
        (output / name).write_bytes((source / name).read_bytes())
    write_new(
        output / "replay.json",
        {
            "scope": "ARCHIVED_REPLAY; no generation or execution",
            "source": str(source.resolve()),
            "request_hash": digest(request),
            "confirmation": False,
        },
    )
    return result

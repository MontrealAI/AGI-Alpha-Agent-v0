# SPDX-License-Identifier: Apache-2.0
"""Non-skippable Docker qualification of the native generated-AST path.

All cases are exposed software development controls, not fresh scientific
confirmation. No candidate is interpreted or executed on the host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.invention_automation import specification as spec
from alpha_factory_v1.core.runtime.invention_automation import (
    specification_run as native,
)
from alpha_factory_v1.core.utils.secure_run import (
    SandboxTimeout,
    SandboxUnavailable,
    secure_run,
)

PROTOCOL: dict[str, Any] = {
    "schema": "agialpha/invention-dynamic-qualification/v1",
    "scope": "exposed Docker software-mechanics qualification; no scientific confirmation or commercial claim",
    "construction_scope": "legacy dimensional constructor is used mechanically, never as a source-claim truth gate",
    "confirmation": False,
    "candidate_count": 2,
    "limits": {
        "wall_seconds": 120,
        "cpus": 2,
        "memory_bytes": 2147483648,
        "pids": 64,
        "scratch_bytes": 16777216,
        "combined_output_bytes": 1048576,
    },
    "acceptance": "all declared controls actually executed and checked; missing/blocked/failed controls fail the job",
    "expected_subchecks": {
        "permissions-network-exec": [
            "root_write",
            "input_write",
            "privilege_escalation",
            "nonroot",
            "capabilities_dropped",
            "no_new_privileges",
            "seccomp_filter",
            "no_docker_socket",
            "no_host_mounts",
            "cpu_limit",
            "memory_limit",
            "pids_limit",
            "scratch_writable",
            "scratch_exec",
            "external_network_denied",
            "no_default_route",
        ],
        "resource-exhaustion": ["scratch_exhaustion", "pids_exhaustion"],
        "verifier-tampering": ["verifier_state", "oracle_source"],
    },
    "independence": "separate read-only verifier process; shared authors, host, model family and standard library",
    "excluded_claims": ["general hostile-code certification", "all container exec denied", "fresh invention benefit"],
}

PERMISSIONS = r"""import errno,json,os,pathlib,socket,subprocess,sys
checks={}
def denied(name,operation):
 try: operation()
 except OSError as error:
  checks[name]=error.errno in (errno.EACCES,errno.EPERM,errno.EROFS,errno.ENOENT)
 else: checks[name]=False
denied("root_write",lambda:open("/alpha-forbidden","w"))
denied("input_write",lambda:open(sys.argv[0],"w"))
denied("privilege_escalation",lambda:os.setuid(0))
checks["nonroot"]=os.getuid()==65534 and os.getgid()==65534
status=dict(line.split(":",1) for line in pathlib.Path("/proc/self/status").read_text().splitlines() if ":" in line)
checks["capabilities_dropped"]=int(status["CapEff"].strip(),16)==0
checks["no_new_privileges"]=status["NoNewPrivs"].strip()=="1"
checks["seccomp_filter"]=status["Seccomp"].strip()=="2"
checks["no_docker_socket"]=not pathlib.Path("/var/run/docker.sock").exists()
checks["no_host_mounts"]=not pathlib.Path("/workspace").exists() and not pathlib.Path("/github").exists()
def limit(name): return pathlib.Path("/sys/fs/cgroup",name).read_text().strip()
limits={name:limit(name) for name in ("cpu.max","memory.max","pids.max")}
cpu,period=map(int,limits["cpu.max"].split())
checks["cpu_limit"]=cpu/period<=2
checks["memory_limit"]=int(limits["memory.max"])<=2147483648
checks["pids_limit"]=int(limits["pids.max"])<=64
probe=pathlib.Path("/tmp/writable")
probe.write_bytes(b"scratch")
checks["scratch_writable"]=probe.read_bytes()==b"scratch"
binary=pathlib.Path("/tmp/forbidden-exec")
binary.write_bytes(pathlib.Path("/bin/true").read_bytes());binary.chmod(0o755)
denied("scratch_exec",lambda:subprocess.run([str(binary)],check=True))
connection=socket.socket();connection.settimeout(0.25)
try: connection.connect(("198.51.100.1",80))
except OSError: checks["external_network_denied"]=True
else: checks["external_network_denied"]=False
finally: connection.close()
checks["no_default_route"]=all(line.split()[1]!="00000000" for line in pathlib.Path("/proc/net/route").read_text().splitlines()[1:])
print(json.dumps({"checks":checks,"observed_cgroup_limits":limits},sort_keys=True))
"""

EXHAUSTION = r"""import errno,json,pathlib,threading
checks={};written=0
try:
 with open("/tmp/scratch-limit","wb") as output:
  for _ in range(18): written+=output.write(b"x"*1048576);output.flush()
except OSError as error: checks["scratch_exhaustion"]=error.errno==errno.ENOSPC
else: checks["scratch_exhaustion"]=False
event=threading.Event();threads=[]
try:
 for _ in range(80):
  thread=threading.Thread(target=event.wait,args=(5,));thread.start();threads.append(thread)
except RuntimeError: checks["pids_exhaustion"]=1<=len(threads)<64
else: checks["pids_exhaustion"]=False
finally:
 event.set()
 for thread in threads: thread.join(timeout=6)
print(json.dumps({"checks":checks,"scratch_bytes_written":written,"threads_started":len(threads)},sort_keys=True))
"""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    with path.open("x") as output:
        output.write(json.dumps(value, sort_keys=True, indent=2) + "\n")


def run_url() -> str | None:
    server = os.getenv("GITHUB_SERVER_URL")
    repository = os.getenv("GITHUB_REPOSITORY")
    run = os.getenv("GITHUB_RUN_ID")
    return f"{server}/{repository}/actions/runs/{run}" if server and repository and run else None


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def require_native_artifact(result: dict[str, Any]) -> None:
    require(
        result.get("executed") is True
        and result.get("status") == "EXECUTED_UNVERIFIED"
        and isinstance(result.get("artifact"), dict),
        "actual native program must return an artifact; a crash or blocked receipt cannot qualify",
    )


def require_probe_receipt(name: str, receipt: dict[str, Any]) -> None:
    checks = receipt.get("checks")
    require(
        isinstance(checks, dict)
        and set(checks) == set(PROTOCOL["expected_subchecks"][name])
        and all(value is True for value in checks.values()),
        "missing, unexpected or failed containment subcheck",
    )


def preflight() -> dict[str, Any]:
    if not shutil.which("docker"):
        raise SandboxUnavailable("Docker unavailable; dynamic qualification cannot pass or skip")
    image = os.getenv("ALPHA_SANDBOX_IMAGE", "")
    if not re.fullmatch(r"[A-Za-z0-9./:_-]+@sha256:[a-f0-9]{64}", image):
        raise SandboxUnavailable("qualification requires an already present digest-pinned image")
    inspected = subprocess.run(
        ["docker", "image", "inspect", image], capture_output=True, text=True, timeout=10, check=False
    )
    require(inspected.returncode == 0, "digest-pinned image absent; harness never pulls images")
    metadata = json.loads(inspected.stdout)[0]
    server = subprocess.run(
        ["docker", "version", "--format", "{{.Server.Version}}"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    require(server.returncode == 0, "Docker daemon unavailable")
    return {"image": image, "image_id": metadata["Id"], "server_version": server.stdout.strip()}


def containers() -> set[str]:
    result = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "name=alpha-sandbox-"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    return set(result.stdout.split())


def oracle(root: Path, output: Path, candidate: str) -> dict[str, Any]:
    command = [
        sys.executable,
        "-B",
        "-m",
        "contrib.invention_automation.dynamic_oracle",
        "--root",
        str(root),
        "--freeze",
        str(output / "freeze.json"),
        "--case",
        str(output / "case.json"),
        "--candidate",
        str(output / f"{candidate}-program.json"),
        "--result",
        str(output / f"{candidate}-result.json"),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=root,
        env={"PATH": os.defpath, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8"},
    )
    write(output / f"{candidate}-oracle-process.json", {"returncode": result.returncode, "stderr": result.stderr})
    require(result.returncode in (0, 2), "separate oracle failed: " + result.stderr[-1000:])
    receipt: dict[str, Any] = json.loads(result.stdout)
    require(receipt.get("tested_denials") == {"candidate_write": True, "socket": True}, "oracle restrictions untested")
    return receipt


def qualify(root: Path, output: Path) -> dict[str, Any]:
    inventory = preflight()
    initial_containers = containers()
    request_path = root / "contrib/invention_automation/specification-request.json"
    request = json.loads(request_path.read_text())
    spec.validate_request(request)
    witness = spec.criticize(request)
    generated = spec.construct(request, spec.constrain(request, witness))
    write(output / "construction.json", generated)
    case = {"requirements": request["requirements"], "records": request["records"]}
    write(output / "case.json", case)
    programs = {"valid": generated["program"], "invalid": {"op": "emit", "status": "CONSISTENT"}}
    for name, program in programs.items():
        write(output / f"{name}-program.json", program)
    protected = output / "verifier-state.txt"
    protected.write_text("host verifier canary; never mounted into candidate\n")
    protected_hash = sha(protected)
    oracle_path = root / "contrib/invention_automation/dynamic_oracle.py"
    oracle_hash = sha(oracle_path)
    mutation_probe = (
        "import errno,json,pathlib\nchecks={}\n"
        f"for name,path in (('verifier_state',{str(protected)!r}),('oracle_source',{str(oracle_path)!r})):\n"
        " try: pathlib.Path(path).write_text('candidate-mutated')\n"
        " except OSError as error: checks[name]=error.errno in (errno.ENOENT,errno.EACCES,errno.EROFS,errno.EPERM)\n"
        " else: checks[name]=False\n"
        "print(json.dumps({'checks':checks},sort_keys=True))\n"
    )
    probes = {
        "permissions-network-exec": PERMISSIONS,
        "resource-exhaustion": EXHAUSTION,
        "verifier-tampering": mutation_probe,
        "excessive-output": "import os\nos.write(1,b'x'*(1048576+8192))\n",
        "timeout": "import time\ntime.sleep(180)\n",
    }
    for name, source in probes.items():
        (output / f"{name}.py").write_text(source)
    source_paths = list(native.source_hashes()) + [
        "contrib/invention_automation/qualify_dynamic.py",
        "contrib/invention_automation/dynamic_oracle.py",
        "contrib/invention_automation/readonly.py",
        "contrib/invention_automation/specification-request.json",
    ]
    freeze = {
        "protocol": PROTOCOL,
        **inventory,
        "source_sha256": {name: sha(root / name) for name in source_paths},
        "driver_sha256": hashlib.sha256(native.DRIVER.encode()).hexdigest(),
        "case_sha256": sha(output / "case.json"),
        "candidate_sha256": {name: sha(output / f"{name}-program.json") for name in programs},
        "probe_sha256": {name: sha(output / f"{name}.py") for name in probes},
        "run_url": run_url(),
        "tested_sha": os.getenv("QUALIFICATION_HEAD_SHA", os.getenv("GITHUB_SHA")),
    }
    write(output / "freeze.json", freeze)
    freeze_identity = sha(output / "freeze.json")
    attempts: list[dict[str, Any]] = []

    def verify_frozen_inventory() -> None:
        require(sha(output / "freeze.json") == freeze_identity, "qualification freeze changed")
        require(os.getenv("ALPHA_SANDBOX_IMAGE") == freeze["image"], "qualification image changed")
        for relative, identity in freeze["source_sha256"].items():
            require(sha(root / relative) == identity, "frozen source changed: " + relative)
        require(sha(output / "case.json") == freeze["case_sha256"], "frozen case changed")
        for name, identity in freeze["candidate_sha256"].items():
            require(sha(output / f"{name}-program.json") == identity, "frozen candidate changed")
        for name, identity in freeze["probe_sha256"].items():
            require(sha(output / f"{name}.py") == identity, "frozen containment probe changed")

    def record(name: str, operation: Callable[[], dict[str, Any]]) -> None:
        start = time.monotonic()
        entered = False
        try:
            verify_frozen_inventory()
            entered = True
            details = operation()
            verify_frozen_inventory()
            entry: dict[str, Any] = {"name": name, "status": "PASS", "details": details}
        except (
            OSError,
            ValueError,
            RuntimeError,
            subprocess.SubprocessError,
            SandboxTimeout,
            KeyError,
            TypeError,
        ) as error:
            entry = {"name": name, "status": "FAIL", "error_type": type(error).__name__, "reason": str(error)}
        entry["wall_seconds"] = time.monotonic() - start
        entry["executed"] = entered
        attempts.append(entry)
        with (output / "attempts.jsonl").open("a") as ledger:
            ledger.write(json.dumps(entry, sort_keys=True) + "\n")
        print(json.dumps({"control": name, "status": entry["status"]}), flush=True)

    def native_case(name: str) -> dict[str, Any]:
        result = native.isolated(programs[name], case["records"])
        write(output / f"{name}-result.json", result)
        require_native_artifact(result)
        receipt = oracle(root, output, name)
        write(output / f"{name}-oracle.json", receipt)
        verdict = "PASS" if name == "valid" else "REJECTED"
        require(receipt["verdict"] == verdict, "separate oracle unexpected verdict")
        if name == "invalid":
            require(
                receipt.get("reason") == "actual record consequences differ from separate oracle",
                "invalid-result control must reject actual wrong consequences, not a crash or schema failure",
            )
        return {"actual_execution": True, "oracle": receipt, "result_sha256": sha(output / f"{name}-result.json")}

    for name in programs:
        record("native-" + name, partial(native_case, name))

    def probe(name: str) -> dict[str, Any]:
        started = time.monotonic()
        try:
            result = secure_run([sys.executable, str((output / f"{name}.py").resolve())])
        except SandboxTimeout:
            require(name == "timeout", "unexpected timeout")
            duration = time.monotonic() - started
            require(115 <= duration <= 150, "native wall timeout outside allowed termination margin")
            require(containers() == initial_containers, "timeout left a candidate container")
            return {"termination": "SandboxTimeout", "observed_seconds": duration}
        except ValueError as error:
            require(name == "excessive-output" and str(error) == "sandbox output exceeds 1 MiB", "unexpected refusal")
            require(containers() == initial_containers, "output termination left a candidate container")
            return {"termination": "output cap", "combined_output_upper_bound": 1048576}
        require(name not in {"timeout", "excessive-output"}, "termination control was not enforced")
        require(result.returncode == 0, "probe failed inside container: " + result.stderr[-1000:])
        receipt: dict[str, Any] = json.loads(result.stdout)
        require_probe_receipt(name, receipt)
        require(sha(protected) == protected_hash and sha(oracle_path) == oracle_hash, "verifier state changed")
        return receipt

    for name in probes:
        record(name, partial(probe, name))
    require(containers() == initial_containers, "qualification left candidate containers")
    require(sha(protected) == protected_hash and sha(oracle_path) == oracle_hash, "verifier state changed")
    verify_frozen_inventory()
    require(len(attempts) == 7, "empty or incomplete qualification selection")
    status = "PASS" if all(attempt["status"] == "PASS" for attempt in attempts) else "FAIL"
    return {
        "status": status,
        "controls_executed": sum(attempt["executed"] for attempt in attempts),
        "attempts": attempts,
        "freeze_sha256": sha(output / "freeze.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        summary = qualify(root, output)
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.SubprocessError,
        SandboxTimeout,
        KeyError,
        TypeError,
    ) as error:
        summary = {
            "status": "BLOCKED" if isinstance(error, SandboxUnavailable) else "FAIL",
            "error_type": type(error).__name__,
            "reason": str(error),
        }
    summary.update({"protocol": PROTOCOL, "run_url": run_url(), "wall_seconds": time.monotonic() - started})
    write(output / "summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

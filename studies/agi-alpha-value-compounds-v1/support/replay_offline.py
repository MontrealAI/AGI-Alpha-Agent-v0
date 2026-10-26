# SPDX-License-Identifier: Apache-2.0
"""Install exact local wheels and replay into a new isolated directory, offline."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FREEZE_SHA256 = "25ee20b1cd68710a5eea65fc08e2eba2f47a521bfde2d9ebbf37731280bc6d64"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_source(root: Path) -> dict:
    raw = (root / "discovery/final-freeze.json").read_bytes()
    if digest(raw) != FREEZE_SHA256:
        raise ValueError("FREEZE_IDENTITY")
    freeze = json.loads(raw)
    for name, row in freeze["files"].items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("FROZEN_SOURCE_NOT_REGULAR: " + name)
        content = path.read_bytes()
        if len(content) != row["bytes"] or digest(content) != row["sha256"]:
            raise ValueError("FROZEN_SOURCE_IDENTITY: " + name)
    native = json.loads((root / "native/SOURCE.json").read_text())
    for row in native["files"]:
        path = root / "native" / row["path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("NATIVE_SOURCE_NOT_REGULAR")
        content = path.read_bytes()
        git = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if digest(content) != row["sha256"] or git != row["git_blob"] or len(content) != row["bytes"]:
            raise ValueError("NATIVE_SOURCE_IDENTITY: " + row["path"])
    return {"freeze_sha256": digest(raw), "frozen_files": len(freeze["files"]),
            "native_files": len(native["files"]), "native_commit": native["commit"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New directory outside the companion package")
    parser.add_argument("--mission", default="httpx-development", help="Existing registered mission ID")
    parser.add_argument("--arm", choices=["incumbent", "retained", "conventional"], default="conventional")
    parser.add_argument("--node", default="node")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise ValueError("OUTPUT_MUST_BE_NEW_AND_OUTSIDE_COMPANION")
    libc, libc_version = platform.libc_ver()
    if (platform.python_implementation() != "CPython" or sys.version_info[:2] != (3, 12)
            or platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}
            or libc != "glibc" or tuple(int(x) for x in libc_version.split(".")[:2]) < (2, 34)):
        raise RuntimeError("SUPPORTED_WHEELS_REQUIRE_CPYTHON_3_12_LINUX_X86_64_GLIBC_2_34")
    node = shutil.which(args.node)
    if node is None:
        raise RuntimeError("NODE_NOT_INSTALLED; Node is an external prerequisite, not a bundled dependency")
    identity = verify_source(ROOT)
    manifest = json.loads((ROOT / "support/dependency-manifest.json").read_text())
    listed = set()
    for row in manifest["wheels"]:
        path = ROOT / row["path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("WHEEL_NOT_REGULAR")
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or digest(raw) != row["sha256"]:
            raise ValueError("WHEEL_IDENTITY: " + row["path"])
        listed.add(path.name)
    if listed != {p.name for p in (ROOT / "deps/wheels").glob("*.whl")}:
        raise ValueError("WHEEL_INVENTORY_CLOSURE")
    registry = json.loads((ROOT / "data/missions.json").read_text())
    if args.mission not in registry["missions"]:
        raise ValueError("UNKNOWN_REGISTERED_MISSION")
    out.mkdir(parents=True)
    logs = out / "logs"
    logs.mkdir()
    (out / "tmp").mkdir()
    (out / "home").mkdir()
    events = []
    started = time.perf_counter()
    env = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "VIRTUAL_ENV"):
        env.pop(key, None)
    env.update({"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PIP_NO_INDEX": "1",
                "PIP_CONFIG_FILE": os.devnull, "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PIP_CACHE_DIR": str(out / "pip-cache"), "TMPDIR": str(out / "tmp")})

    def run(label: str, command: list[str], cwd: Path, execution_env: dict | None = None) -> subprocess.CompletedProcess:
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        tick = time.perf_counter()
        result = subprocess.run(command, cwd=cwd, env=execution_env or env, capture_output=True, check=False)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        (logs / (label + ".stdout.txt")).write_bytes(result.stdout)
        (logs / (label + ".stderr.txt")).write_bytes(result.stderr)
        event = {"label": label, "command": command, "cwd": str(cwd), "exit_code": result.returncode,
                 "wall_seconds": time.perf_counter() - tick,
                 "observed_child_cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
                 "stdout_bytes": len(result.stdout), "stderr_bytes": len(result.stderr)}
        events.append(event)
        (out / "operations.json").write_text(json.dumps(events, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(f"{label} failed with {result.returncode}; original logs retained in {logs}")
        return result

    stage = out / "study"
    stage.mkdir()
    try:
        # The frozen pipeline prepends deps/site. That cache is deliberately absent
        # in this fresh copy; all third-party imports must resolve from the new venv.
        for name in ("src", "tests", "native", "data", "curation"):
            shutil.copytree(ROOT / name, stage / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (stage / "discovery").mkdir()
        shutil.copyfile(ROOT / "protocol.json", stage / "protocol.json")
        shutil.copyfile(ROOT / "discovery/final-freeze.json", stage / "discovery/final-freeze.json")
        shutil.copyfile(ROOT / "discovery/confirmation-metadata-v3.json", stage / "discovery/confirmation-metadata-v3.json")
        shutil.copytree(ROOT / "discovery/canonical", stage / "discovery/canonical")
        verify_source(stage)
        venv = out / "venv"
        run("create-venv", [sys.executable, "-m", "venv", "--copies", str(venv)], out)
        python = venv / "bin/python"
        env["VIRTUAL_ENV"] = str(venv)
        env["PATH"] = str(venv / "bin") + os.pathsep + env.get("PATH", "")
        run("install-locked-wheels", [str(python), "-m", "pip", "install", "--no-index", "--require-hashes",
            "--only-binary=:all:", "--find-links", str(ROOT / "deps/wheels"),
            "-r", str(ROOT / "support/requirements-replay.lock")], out)
        run("dependency-check", [str(python), "-m", "pip", "check"], out)
        env["PYTHONPATH"] = str(stage / "src")
        env["PYTHON_EXECUTABLE"] = str(python)
        probe = '''import importlib,importlib.metadata,json,sys
from pathlib import Path
import pipeline
expected=json.loads(sys.argv[1]); versions={n:importlib.metadata.version(n) for n in expected}
assert versions==expected,(versions,expected)
assert sys.prefix!=sys.base_prefix
modules={n:importlib.import_module(n) for n in ['griffe','pydantic','pydantic_core','cryptography','cffi','pycparser','typing_extensions','typing_inspection','annotated_types','colorama']}
origins={n:str(Path(m.__file__).resolve()) for n,m in modules.items()}
assert all(Path(p).is_relative_to(Path(sys.prefix)) for p in origins.values()),origins
print(json.dumps({'python':sys.version,'executable':sys.executable,'prefix':sys.prefix,'versions':versions,'origins':origins,'pip_bootstrap_version':importlib.metadata.version('pip'),'native_inventory_module':pipeline.reference_report.__module__}))
'''
        expected = {row["name"]: row["version"] for row in manifest["wheels"]}
        environment = run("environment", [str(python), "-c", probe, json.dumps(expected)], stage)
        (out / "environment.json").write_bytes(environment.stdout)
        shared = run("shared-tests", [str(python), "-m", "unittest", "discover", "-s", str(stage / "tests"), "-p", "test_*.py", "-v"], stage)
        match = re.search(rb"Ran (\d+) tests", shared.stderr)
        if not match or int(match[1]) != 75:
            raise ValueError("EXPECTED_75_SHARED_TESTS")
        candidate = run("candidate-crosscheck", [str(python), str(ROOT / "support/candidate_crosscheck.py"), "--root", str(stage)], stage)
        candidate_result = json.loads(candidate.stdout)
        if candidate_result["tests_run"] != 47 or not candidate_result["success"]:
            raise ValueError("EXPECTED_47_CANDIDATE_CROSSCHECKS")
        node_version = run("node-version", [node, "--version"], out).stdout.decode().strip()
        run("economics-tests", [node, "--test", str(stage / "tests/economics.test.mjs")], stage)
        workbench = run("workbench", [node, str(stage / "src/workbench.mjs"), args.mission, args.arm, str(out / "mission")], stage)
        inspection = json.loads((out / "mission/inspection.json").read_text())
        if (inspection["authentication"] != "UNAUTHENTICATED_HISTORICAL_IMPORT"
                or inspection["activeProof"] != [] or inspection["activeAuthority"] != []):
            raise ValueError("NATIVE_AUTHORITY_BOUNDARY_CHANGED")
        verify_source(ROOT)
        verify_source(stage)
        summary = {"schema": "value-compounds-offline-replay/v1", "success": True,
                   "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source": identity,
                   "platform": platform.platform(), "python": platform.python_version(), "node": node_version,
                   "node_matches_observed_runtime": node_version == "v24.22.1",
                   "wheel_distributions": len(manifest["wheels"]), "missing_required_dependencies": [],
                   "shared_tests": 75, "candidate_crosschecks": 47,
                   "seeded_pairs_are_cases_within_one_test": 150,
                   "mission": args.mission, "arm": args.arm, "workbench": json.loads(workbench.stdout),
                   "native_authentication": inspection["authentication"], "active_authority": [],
                   "wall_seconds": time.perf_counter() - started,
                   "observed_child_cpu_seconds": sum(event["observed_child_cpu_seconds"] for event in events),
                   "inference_tokens": None, "inference_usd": None, "new_customer_jobs": 0,
                   "network_requested_by_support": False,
                   "network_limit": "pip uses no-index; selected static local workflows make no runtime network calls. No kernel-level network sandbox is claimed.",
                   "role": "Independent environment replay of frozen development and selected registered mission; original primary outputs unchanged"}
        (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary))
    except Exception as error:
        failure = {"schema": "value-compounds-offline-replay/v1", "success": False,
                   "error": type(error).__name__ + ": " + str(error), "operations_completed": len(events),
                   "wall_seconds": time.perf_counter() - started, "inference_usd": None,
                   "original_logs_preserved": True}
        (out / "FAILED.json").write_text(json.dumps(failure, indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()

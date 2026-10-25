# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
import hashlib
import io
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUNNER = "contrib/productive-capability-ledger/automation-v1/run-mission.mjs"
VERIFIER = "contrib/productive-capability-ledger/automation-v1/verify-run.py"
PAYLOADS = (
    "plan.json",
    "declared-inventory.csv",
    "observed-inventory.csv",
    "differences.csv",
    "action-plan.csv",
    "workspace.json",
    "report.md",
    "final-acceptance.json",
)
SOURCES = (
    RUNNER,
    VERIFIER,
    "examples/ti-guide/guide.mjs",
    "examples/successor-alpha/engine.mjs",
    "examples/successor-alpha/research.mjs",
    "docs/assets/successor/engine.mjs",
    "contrib/productive-capability-ledger/transport-v1/bridge.mjs",
    "contrib/productive-capability-ledger/transport-v1/source_worker.py",
    "contrib/productive-capability-ledger/transport-v1/serve_candidate.py",
    "contrib/productive-capability-ledger/transport-v1/strategy.html",
    "contrib/productive-capability-ledger/transport-v1/strategy.js",
    "contrib/productive-capability-ledger/transport-v1/strategy.css",
    "contrib/strategy_succession/transport/strategy_executor.py",
    "contrib/strategy_succession/serve.py",
    "contrib/strategy_succession/ENGINEERING_MANIFEST.json",
    "contrib/strategy_succession/requirements-qualification.txt",
)
SHA = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def _read(path: Path, maximum: int = 1_000_000) -> bytes:
    parent = path.parent
    while parent != parent.parent:
        if parent.is_symlink():
            raise ValueError("file ancestry changed to a link")
        parent = parent.parent
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("bounded ordinary file required")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))

    def identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_size > maximum
            or identity(info) != identity(before)
        ):
            raise ValueError("bounded unchanged ordinary file required")
        data = bytearray()
        while len(data) <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        if len(data) > maximum:
            raise ValueError("file exceeded its bound")
        if identity(os.fstat(fd)) != identity(info) or identity(path.lstat()) != identity(info):
            raise ValueError("file changed during inspection")
        return bytes(data)
    finally:
        os.close(fd)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field refused")
        result[key] = value
    return result


def _path(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z0-9_./-]+", value)
        or value.startswith("/")
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise ValueError("explicit repository-relative source path required")
    return value


class SourceAssuranceWorker:
    def __init__(
        self, registry: Path, output_root: Path, *, node: Path, git: Path, python: Path = Path(sys.executable)
    ) -> None:
        self.registry, self.output_root = registry.absolute(), output_root.absolute()
        self.root = ROOT
        self.node, self.git, self.python = self._executable(node), self._executable(git), self._executable(python)
        if git.name != "git":
            raise ValueError("the fixed runner requires an operator-selected Git executable named git")
        self.registry_bytes = _read(self.registry, 32768)
        value = json.loads(self.registry_bytes, object_pairs_hook=_unique)
        if not isinstance(value, dict) or set(value) != {"schema", "scopes", "maxSeconds"}:
            raise ValueError("candidate registry fields changed")
        if value["schema"] != "alpha-source-assurance-candidate-profile/v1":
            raise ValueError("unsupported candidate registry")
        self.max_seconds = value["maxSeconds"]
        if type(self.max_seconds) is not int or not 1 <= self.max_seconds <= 60:
            raise ValueError("candidate time limit must be 1–60 seconds")
        scopes = value["scopes"]
        if not isinstance(scopes, dict) or not 1 <= len(scopes) <= 32:
            raise ValueError("candidate needs 1–32 exact public scopes")
        for ident, scope in scopes.items():
            if not IDENT.fullmatch(ident) or not isinstance(scope, dict) or set(scope) != {"manifestPath", "sourceRef"}:
                raise ValueError("candidate scope fields changed")
            _path(scope["manifestPath"])
            if not isinstance(scope["sourceRef"], str) or not re.fullmatch(r"[0-9a-f]{40}", scope["sourceRef"]):
                raise ValueError("candidate requires exact local Git commit")
        self.scopes = scopes
        self.identities = {name: hashlib.sha256(_read(ROOT / name, 8_000_000)).hexdigest() for name in SOURCES}

    @staticmethod
    def _executable(path: Path) -> str:
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError("operator-selected absolute interpreter required")
        return str(path)

    def _sources(self) -> None:
        if _read(self.registry, 32768) != self.registry_bytes:
            raise ValueError("candidate scope registry changed")
        for name, expected in self.identities.items():
            if hashlib.sha256(_read(ROOT / name, 8_000_000)).hexdigest() != expected:
                raise ValueError("candidate implementation changed")
        current = self.output_root
        while current != current.parent:
            if current.is_symlink():
                raise ValueError("candidate output may not traverse linked directories")
            current = current.parent

    def _process(
        self, args: list[str], payload: dict[str, Any] | None, seconds: float, checkpoint: Callable[..., None]
    ) -> dict[str, Any]:
        environment = {
            "PATH": os.pathsep.join(dict.fromkeys(str(Path(p).parent) for p in (self.git, self.node, self.python))),
            "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
        }
        deadline = time.monotonic() + seconds
        checkpoint()
        with tempfile.TemporaryFile() as stdin, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            stdin.write(_canonical(payload) if payload is not None else b"")
            stdin.seek(0)
            child = subprocess.Popen(
                args, cwd=ROOT, env=environment, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True
            )
            try:
                while child.poll() is None:
                    checkpoint()
                    if time.monotonic() >= deadline:
                        raise ValueError("candidate child elapsed budget exhausted")
                    if os.fstat(stdout.fileno()).st_size > 1_000_000 or os.fstat(stderr.fileno()).st_size > 65536:
                        raise ValueError("candidate child output exceeded its bound")
                    time.sleep(0.02)
                checkpoint()
                if child.returncode != 0:
                    raise ValueError("candidate fixed child refused; inspect retained artifacts")
                self._kill(child)
                if os.fstat(stderr.fileno()).st_size > 65536:
                    raise ValueError("candidate child stderr exceeded its bound")
                stdout.seek(0)
                data = stdout.read(1_000_001)
                if len(data) > 1_000_000:
                    raise ValueError("candidate child output exceeded its bound")
                result = json.loads(data)
                if not isinstance(result, dict):
                    raise ValueError("candidate fixed child needs an object result")
                return result
            finally:
                self._kill(child)

    @staticmethod
    def _kill(child: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        if child.poll() is None:
            child.wait(timeout=5)

    def prepare_input(self, scope_id: str, run_id: str, *, created_at: str, expires_at: str) -> dict[str, Any]:
        self._sources()
        if scope_id not in self.scopes or not IDENT.fullmatch(run_id):
            raise ValueError("select one configured public scope and a fresh bounded run identity")
        options = {
            **self.scopes[scope_id],
            "runId": run_id,
            "createdAt": created_at,
            "expiresAt": expires_at,
            "maxSeconds": self.max_seconds,
            "maxAttempts": 1,
            "maxTotalSeconds": self.max_seconds,
        }
        result = self._process(
            [self.node, "--max-old-space-size=256", str(HERE / "bridge.mjs")],
            {"operation": "plan", "options": options},
            self.max_seconds,
            lambda: None,
        )
        return {"scope_id": scope_id, "plan": result["plan"], "approval_digest": result["approvalDigest"]}

    def _payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) != {"scope_id", "plan", "approval_digest"}:
            raise ValueError("candidate input fields changed")
        if not isinstance(payload["scope_id"], str):
            raise ValueError("candidate scope identity must be a string")
        scope = self.scopes.get(payload["scope_id"])
        plan = payload["plan"]
        if scope is None or not isinstance(plan, dict):
            raise ValueError("public scope not installed")
        required = {
            "schema": "alpha-source-assurance-plan/v3",
            "offeringId": "committed-source-assurance",
            **scope,
            "maxSeconds": self.max_seconds,
            "maxAttempts": 1,
            "maxTotalSeconds": self.max_seconds,
            "authority": "none",
        }
        if any(plan.get(k) != v for k, v in required.items()) or not IDENT.fullmatch(plan.get("runId", "")):
            raise ValueError("candidate plan differs from installed public scope or bounds")
        if not isinstance(payload["approval_digest"], str) or not SHA.fullmatch(payload["approval_digest"]):
            raise ValueError("exact source approval digest required")
        if hashlib.sha256(_canonical(plan)).hexdigest() != payload["approval_digest"]:
            raise ValueError("source approval digest changed")
        return plan

    def execute(
        self, method: str, payload: dict[str, Any], limits: dict[str, Any], checkpoint: Callable[..., None]
    ) -> dict[str, Any]:
        self._sources()
        if method != "run-mission" or limits.get("allow_native") is not False:
            raise ValueError("candidate supports only fixed source assurance with native execution disabled")
        wall = limits.get("wall_seconds")
        if (
            not isinstance(wall, (int, float))
            or isinstance(wall, bool)
            or not math.isfinite(wall)
            or wall < self.max_seconds * 2 + 5
        ):
            raise ValueError("installed lease must cover bounded run and independent verification")
        if (
            limits.get("service_work") != 1
            or any(limits.get(k) != 0 for k in ("improvement_work", "native_calls", "native_solve_seconds"))
            or not SHA.fullmatch(limits.get("source_hash", ""))
        ):
            raise ValueError("candidate requires exactly one separately reserved service unit")
        plan = self._payload(payload)
        checkpoint(service_work=1)
        result = self._process(
            [self.node, "--max-old-space-size=256", str(HERE / "bridge.mjs")],
            {
                "operation": "run",
                "plan": plan,
                "approvalDigest": payload["approval_digest"],
                "outputRoot": str(self.output_root),
            },
            self.max_seconds + 1,
            checkpoint,
        )
        directory = self.output_root / plan["runId"]
        acceptance = self._process(
            [self.python, "-I", str(ROOT / VERIFIER), str(directory)], None, self.max_seconds, checkpoint
        )
        if (
            result.get("accepted") is not True
            or acceptance.get("accepted") is not True
            or result.get("runId") != plan["runId"]
            or acceptance.get("runId") != plan["runId"]
        ):
            raise ValueError("independent source acceptance did not match the approved mission")
        complete_bytes = _read(directory / "COMPLETE.json", 1_000_000)
        if hashlib.sha256(complete_bytes).hexdigest() != acceptance.get("completeSha256"):
            raise ValueError("completion changed after independent verification")
        complete = json.loads(complete_bytes, object_pairs_hook=_unique)
        if not isinstance(complete.get("artifacts"), dict):
            raise ValueError("completion artifact inventory missing")
        buffer = io.BytesIO()
        size = 0
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in PAYLOADS:
                checkpoint()
                data = _read(directory / name, 512_000)
                if hashlib.sha256(data).hexdigest() != complete["artifacts"].get(name):
                    raise ValueError("customer artifact changed after independent verification")
                size += len(data)
                if size > 512_000:
                    raise ValueError("customer package exceeded candidate output bound; retain for inspection")
                archive.writestr(name, data)
            archive.writestr("independent-acceptance.json", _canonical(acceptance))
        if _read(directory / "COMPLETE.json", 1_000_000) != complete_bytes:
            raise ValueError("completion changed while packaging verified artifacts")
        bundle = buffer.getvalue()
        checkpoint()
        self._sources()
        return {
            "result": {
                "schema": "alpha-source-assurance-candidate-outcome/v1",
                "runId": plan["runId"],
                "sourceRef": plan["sourceRef"],
                "approvalDigest": payload["approval_digest"],
                "independentAcceptance": acceptance,
                "download": {
                    "filename": plan["runId"] + ".zip",
                    "mime": "application/zip",
                    "sha256": hashlib.sha256(bundle).hexdigest(),
                    "bytes": len(bundle),
                    "base64": base64.b64encode(bundle).decode("ascii"),
                },
                "operationalAdoption": "NOT APPROVED",
                "customerAcceptance": "unknown",
            },
            "costs": {
                "service_work": 1,
                "improvement_work": 0,
                "native_calls": 0,
                "native_solve_seconds": 0,
                "unknown_costs": ["complete currency cost", "setup and maintenance", "customer effort"],
            },
            "source_hash": limits["source_hash"],
            "verified": True,
        }


def candidate_policy(journal: Any, worker: SourceAssuranceWorker, *, max_requests: int = 4) -> Any:
    transport = load_transport()
    ExecutorPolicy, Limits, SourceFile = transport.ExecutorPolicy, transport.Limits, transport.SourceFile

    expected_root = journal.root.absolute() / "source-assurance"
    if worker.output_root != expected_root:
        raise ValueError("candidate output root must be inside the existing journal home")
    environment = qualified_candidate_environment(worker)
    sources = tuple(SourceFile(name, ROOT / name, digest) for name, digest in worker.identities.items())
    sources += tuple(
        SourceFile("runtime/" + name, path, expected) for name, path, expected in environment["runtime_sources"]
    )
    sources += (
        SourceFile("candidate-public-scopes.json", worker.registry, hashlib.sha256(worker.registry_bytes).hexdigest()),
    )
    return ExecutorPolicy(
        "source-assurance-candidate-v1",
        sources,
        {"run-mission": Limits(1)},
        Limits(max_requests),
        max_requests=max_requests,
        request_seconds=worker.max_seconds * 2 + 5,
        grant_seconds=worker.max_seconds * 2 + 60,
        max_output_bytes=1_000_000,
    )


def load_transport() -> Any:
    path = ROOT / "contrib/strategy_succession/transport/strategy_executor.py"
    name = "alpha_source_candidate_transport_" + hashlib.sha256(_read(path)).hexdigest()[:16]
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ValueError("existing transport module unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def qualified_candidate_environment(worker: SourceAssuranceWorker) -> dict[str, Any]:
    import importlib.metadata
    import alpha_factory_v1
    from strategy_succession_engineering import serve as engineering

    worker._sources()
    profile_path = ROOT / "contrib/strategy_succession/ENGINEERING_MANIFEST.json"
    profile = json.loads(_read(profile_path), object_pairs_hook=_unique)
    installed_helper = Path(engineering.__file__)
    if hashlib.sha256(_read(installed_helper)).hexdigest() != worker.identities["contrib/strategy_succession/serve.py"]:
        raise ValueError("existing installed environment helper differs from candidate source")
    qualified_node = engineering.qualified_environment(profile["qualified_environment"])
    if Path(worker.node).resolve() != Path(qualified_node).resolve():
        raise ValueError("candidate selected Node differs from the qualified executable")
    child = engineering.qualified_child_environment(worker, profile["qualified_environment"], native=False)
    if importlib.metadata.version("alpha-factory-v1") != "1.42.0" or profile["qualified_runtime_versions"] != [
        "1.42.0"
    ]:
        raise ValueError("candidate requires the public qualified Alpha 1.42 runtime")
    package_root = Path(alpha_factory_v1.__file__).resolve().parent
    for name, expected in profile["runtime_python_files"].items():
        _path(name)
        if hashlib.sha256(_read(package_root / name, 8_000_000)).hexdigest() != expected:
            raise ValueError("public Alpha runtime source differs from qualified profile")
    probe = worker._process(
        [
            worker.node,
            "--max-old-space-size=256",
            "-e",
            "const{execFileSync}=require('node:child_process');process.stdout.write(JSON.stringify({git:execFileSync('git',['--version'],{encoding:'utf8',timeout:5000,maxBuffer:4096}).trim()}));",
        ],
        None,
        6,
        lambda: None,
    )
    if probe != {"git": "git version 2.51.1"}:
        raise ValueError("candidate requires the declared Git 2.51.1 executable")
    return {
        "schema": "alpha-source-candidate-environment/v1",
        "profile": profile["qualified_environment"],
        "git_version": "2.51.1",
        "child_environment": child,
        "operator_adoption": "NOT APPROVED",
        "runtime_sources": [
            (name, package_root / name, profile["runtime_python_files"][name])
            for name in profile["runtime_enforcement_files"]
        ],
    }

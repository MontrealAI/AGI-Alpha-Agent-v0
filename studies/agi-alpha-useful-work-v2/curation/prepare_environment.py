# SPDX-License-Identifier: Apache-2.0
"""Acquire a declared component environment, then install it without an index.

Only explicitly supplied plans are processed. This utility does not select new
missions, resolve unpinned dependencies, run consumers, or qualify an application.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile

from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.specifiers import SpecifierSet
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
from pip._vendor.packaging.version import Version

MAX_REQUESTS = 20
MAX_RESPONSE_BYTES = 20_000_000
MAX_NETWORK_BYTES = 64_000_000
COMPONENT_PACKAGES = {"starlette", "anyio", "pydantic", "pydantic-core", "annotated-types",
                      "typing-extensions", "typing-inspection", "idna", "fastapi", "annotated-doc"}


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def active_requirements(info: dict) -> list[Requirement]:
    env = default_environment()
    env["extra"] = ""
    requirements = [Requirement(text) for text in (info.get("requires_dist") or [])]
    return [item for item in requirements if item.marker is None or item.marker.evaluate(env)]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("REDIRECT_NOT_PERMITTED")


class Preparation:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.out = args.out.resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        for name in ("metadata", "wheels", "licenses", "logs"):
            (self.out / name).mkdir()
        self.events: list[dict] = []
        self.requests = 0
        self.network_bytes = 0
        self.steps: list[dict] = []
        self.wheels: list[dict] = []
        self.metadata: dict[str, dict] = {}
        self.start = time.perf_counter()
        self.cpu = time.process_time()
        self.children = resource.getrusage(resource.RUSAGE_CHILDREN)
        self.started_at = now()
        self.opener = urllib.request.build_opener(NoRedirect())
        self.event("preparation_started", plan=str(args.plan.resolve()), offline=args.offline)

    def event(self, event_type: str, **details) -> None:
        record = {"event": event_type, "utc": now(), **details}
        self.events.append(record)
        with (self.out / "operations.jsonl").open("a") as output:
            output.write(json.dumps(record, sort_keys=True) + "\n")

    def fetch(self, url: str, kind: str) -> bytes:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.username or parsed.password:
            raise ValueError("UNSUPPORTED_URL")
        expected_host = "pypi.org" if kind == "metadata" else "files.pythonhosted.org"
        if parsed.netloc != expected_host:
            raise ValueError("UNSUPPORTED_HOST")
        if self.args.offline:
            raise ValueError("MISSING_OFFLINE_INPUT: " + url)
        if self.requests >= MAX_REQUESTS:
            raise ValueError("REQUEST_LIMIT")
        self.requests += 1
        start, cpu = time.perf_counter(), time.process_time()
        record = {"url": url, "kind": kind, "success": False, "bytes": 0}
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "AGIALPHA-component-study/2"})
            with self.opener.open(request, timeout=30) as response:
                remaining = min(MAX_RESPONSE_BYTES, MAX_NETWORK_BYTES - self.network_bytes)
                raw = response.read(remaining + 1)
                record["http_status"] = response.status
            record["bytes"] = len(raw)
            self.network_bytes += len(raw)
            if len(raw) > remaining or self.network_bytes > MAX_NETWORK_BYTES:
                raise ValueError("NETWORK_BYTE_LIMIT")
            record.update(success=True, sha256=sha(raw))
            return raw
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            record.update(wall_seconds=time.perf_counter() - start, cpu_seconds=time.process_time() - cpu)
            self.event("network_request", **record)

    def get_metadata(self, name: str, version: str) -> dict:
        for directory in self.args.metadata_reuse:
            for path in sorted(directory.glob("*.json")):
                raw = path.read_bytes()
                value = json.loads(raw)
                info = value.get("info", {})
                if canonicalize_name(info.get("name", "")) == name and info.get("version") == version:
                    self.event("metadata_reused", package=name, version=version, source=str(path), sha256=sha(raw))
                    destination = self.out / "metadata" / f"{name}-{version}.json"
                    destination.write_bytes(raw)
                    return value
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        raw = self.fetch(url, "metadata")
        value = json.loads(raw)
        (self.out / "metadata" / f"{name}-{version}.json").write_bytes(raw)
        info = value["info"]
        if canonicalize_name(info["name"]) != name or info["version"] != version:
            raise ValueError("METADATA_IDENTITY")
        return value

    def check_closure(self, pins: dict[str, str]) -> list[dict]:
        checks = []
        for name, metadata in self.metadata.items():
            info = metadata["info"]
            if info.get("requires_python") and platform.python_version() not in SpecifierSet(info["requires_python"]):
                raise ValueError("PYTHON_REQUIREMENT: " + name)
            for requirement in active_requirements(info):
                dependency = canonicalize_name(requirement.name)
                if requirement.url or requirement.extras:
                    raise ValueError("UNSUPPORTED_ACTIVE_DEPENDENCY: " + str(requirement))
                accepted = dependency in pins and Version(pins[dependency]) in requirement.specifier
                checks.append({"from": name, "requirement": str(requirement), "satisfied": accepted})
                if not accepted:
                    raise ValueError("INCOMPLETE_COMPONENT_CLOSURE: " + str(requirement))
        return checks

    def incoming_checks(self, pins: dict[str, str], sources: list[str]) -> list[dict]:
        checks = []
        for text in sources:
            path = Path(text)
            raw = path.read_bytes()
            info = json.loads(raw)["info"]
            for requirement in active_requirements(info):
                name = canonicalize_name(requirement.name)
                if name not in pins:
                    continue
                accepted = Version(pins[name]) in requirement.specifier
                checks.append({"source": str(path), "sha256": sha(raw), "from": info["name"],
                               "from_version": info["version"], "requirement": str(requirement),
                               "component_version": pins[name], "satisfied": accepted})
                if not accepted:
                    raise ValueError("INCOMING_PROFILE_CONSTRAINT: " + str(requirement))
        return checks

    def acquire_wheel(self, name: str, version: str, native_hashes: str, unchanged: list[str]) -> None:
        metadata = self.metadata[name]
        tags = {tag: index for index, tag in enumerate(sys_tags())}
        candidates = []
        for item in metadata["urls"]:
            if item["packagetype"] != "bdist_wheel" or item.get("yanked"):
                continue
            wheel_name, wheel_version, _, supported = parse_wheel_filename(item["filename"])
            if wheel_name != name or str(wheel_version) != version:
                continue
            ranks = [tags[tag] for tag in supported if tag in tags]
            if ranks:
                candidates.append((min(ranks), item["filename"], item))
        if not candidates:
            raise ValueError("NO_COMPATIBLE_WHEEL: " + name)
        item = min(candidates)[2]
        filename, expected = item["filename"], item["digests"]["sha256"]
        if Path(filename).name != filename or len(expected) != 64:
            raise ValueError("INVALID_WHEEL_IDENTITY")
        if name in unchanged and expected not in native_hashes:
            raise ValueError("UNCHANGED_WHEEL_NOT_IN_NATIVE_LOCK: " + name)
        raw, source = None, None
        for directory in self.args.wheel_reuse:
            candidate = directory / filename
            if candidate.exists():
                raw = candidate.read_bytes()
                source = str(candidate)
                if sha(raw) != expected:
                    self.event("wheel_reuse_hash_mismatch", package=name, source=source,
                               observed=sha(raw), expected=expected)
                    raise ValueError("REUSED_WHEEL_HASH_MISMATCH")
                self.event("wheel_reused", package=name, version=version, source=source,
                           bytes=len(raw), sha256=expected)
                break
        if raw is None:
            raw = self.fetch(item["url"], "wheel")
        if len(raw) != item["size"] or sha(raw) != expected:
            raise ValueError("WHEEL_SIZE_OR_HASH_MISMATCH")
        destination = self.out / "wheels" / filename
        destination.write_bytes(raw)
        licenses = []
        with zipfile.ZipFile(destination) as archive:
            for member in archive.infolist():
                base = Path(member.filename).name.lower()
                if ".dist-info/" not in member.filename or not base.startswith(("license", "copying", "notice")):
                    continue
                if member.is_dir() or member.file_size > 1_000_000:
                    raise ValueError("LICENSE_MEMBER_BOUND")
                notice = archive.read(member)
                target = self.out / "licenses" / f"{name}-{version}-{len(licenses) + 1}-{Path(member.filename).name}"
                target.write_bytes(notice)
                licenses.append({"wheel_member": member.filename, "path": str(target.relative_to(self.out)),
                                 "bytes": len(notice), "sha256": sha(notice)})
        self.wheels.append({"name": name, "version": version, "filename": filename, "sha256": expected,
                            "bytes": len(raw), "url": item["url"], "reused_from": source,
                            "native_lock_hash_present": expected in native_hashes,
                            "license_expression": metadata["info"].get("license_expression"),
                            "license_metadata": metadata["info"].get("license"), "license_files": licenses})

    def command(self, command: list[str], label: str) -> str:
        start = time.perf_counter()
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        env = dict(os.environ, PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
        timeout = False
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=180, env=env, check=False)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            timeout = True
            stdout = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = (exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            code = None
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        (self.out / "logs" / f"{label}.stdout").write_text(stdout)
        (self.out / "logs" / f"{label}.stderr").write_text(stderr)
        record = {"command": command, "label": label, "exit_code": code, "timeout": timeout,
                  "wall_seconds": time.perf_counter() - start,
                  "child_cpu_seconds": after.ru_utime + after.ru_stime - children.ru_utime - children.ru_stime,
                  "stdout_sha256": sha(stdout.encode()), "stderr_sha256": sha(stderr.encode())}
        self.steps.append(record)
        self.event("setup_command", **record)
        if code != 0:
            raise ValueError("SETUP_COMMAND_FAILED: " + label)
        return stdout

    def run(self) -> dict:
        error, checks, incoming, inventory, bridge = None, [], [], None, None
        plan = json.loads(self.args.plan.read_text())
        (self.out / "plan.json").write_bytes(self.args.plan.read_bytes())
        try:
            if sys.version_info[:2] != (3, 12) or platform.system() != "Linux" or platform.machine() != "x86_64":
                raise ValueError("SUPPORTED_BOUNDARY_IS_PYTHON312_LINUX_X86_64")
            if plan["phase"] not in {"development", "confirmation"}:
                raise ValueError("UNKNOWN_PLAN_PHASE")
            if plan["phase"] == "confirmation":
                freeze = self.args.confirmation_freeze
                if freeze is None or sha(freeze.read_bytes()) != plan.get("confirmation_freeze_sha256"):
                    raise ValueError("CONFIRMATION_FREEZE_IDENTITY_REQUIRED")
            pins = {canonicalize_name(name): version for name, version in plan["pins"].items()}
            if set(pins) != COMPONENT_PACKAGES:
                raise ValueError("PLAN_MUST_DECLARE_COMPLETE_TEN_PACKAGE_COMPONENT_CLOSURE")
            for name, constraint in plan["declared_component_constraints"].items():
                if Version(pins[name]) not in SpecifierSet(constraint):
                    raise ValueError("DECLARED_COMPONENT_CONSTRAINT: " + name)
            native = Path(plan["native_lock"])
            native_raw = native.read_bytes()
            if sha(native_raw) != plan["native_lock_sha256"]:
                raise ValueError("NATIVE_LOCK_IDENTITY")
            for name, version in pins.items():
                self.metadata[name] = self.get_metadata(name, version)
            checks = self.check_closure(pins)
            incoming = self.incoming_checks(pins, plan["incoming_constraint_metadata"])
            for name, version in pins.items():
                self.acquire_wheel(name, version, native_raw.decode(), plan["unchanged_native_packages"])
            lock = "".join(f"{r['name']}=={r['version']} --hash=sha256:{r['sha256']}\n" for r in self.wheels)
            (self.out / "requirements.lock").write_text(lock)
            python = self.out / "venv/bin/python"
            self.command([sys.executable, "-m", "venv", str(self.out / "venv")], "create-venv")
            self.command([str(python), "-m", "pip", "--isolated", "install", "--no-input", "--no-index",
                          "--no-cache-dir", "--no-compile", "--find-links", str(self.out / "wheels"),
                          "--require-hashes", "-r", str(self.out / "requirements.lock")], "install")
            self.command([str(python), "-m", "pip", "--isolated", "check"], "pip-check")
            inventory = json.loads(self.command([str(python), "-m", "pip", "--isolated", "list", "--format=json"],
                                                "installed-distributions"))
            installed = {canonicalize_name(row["name"]): row["version"] for row in inventory}
            if any(installed.get(name) != version for name, version in pins.items()):
                raise ValueError("INSTALLED_VERSION_IDENTITY")
            bridge_code = (
                "import json; from fastapi import Request; from fastapi.responses import JSONResponse; "
                "import starlette.requests; import starlette.responses; "
                "print(json.dumps({'Request_module': Request.__module__, "
                "'Request_qualname': Request.__qualname__, 'JSONResponse_module': JSONResponse.__module__, "
                "'JSONResponse_qualname': JSONResponse.__qualname__, "
                "'Request_identity': Request is starlette.requests.Request, "
                "'JSONResponse_identity': JSONResponse is starlette.responses.JSONResponse}))"
            )
            bridge = json.loads(self.command([str(python), "-c", bridge_code], "fastapi-import-bridge"))
            if not bridge["Request_identity"] or not bridge["JSONResponse_identity"]:
                raise ValueError("FASTAPI_BRIDGE_IDENTITY_CHANGED")
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self.event("preparation_failed", error=error)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        files = [path for path in self.out.rglob("*") if path.is_file() and not path.is_symlink()]
        result = {"schema": "component-environment-preparation/v1", "environment_id": plan.get("environment_id"),
                  "phase": plan.get("phase"), "started_at": self.started_at, "completed_at": now(),
                  "complete": error is None, "error": error, "python": sys.version,
                  "builder_sha256": sha(Path(__file__).read_bytes()), "plan_sha256": sha(self.args.plan.read_bytes()),
                  "wheels": self.wheels, "closure_checks": checks, "incoming_profile_checks": incoming,
                  "installed_distributions": inventory, "fastapi_import_bridge": bridge, "steps": self.steps,
                  "network_requests": self.requests, "network_response_bytes": self.network_bytes,
                  "wheel_bytes_reused": sum(item["bytes"] for item in self.wheels if item["reused_from"]),
                  "wall_seconds": time.perf_counter() - self.start,
                  "process_cpu_seconds": time.process_time() - self.cpu,
                  "child_cpu_seconds": (children.ru_utime + children.ru_stime
                                        - self.children.ru_utime - self.children.ru_stime),
                  "self_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  "child_peak_rss_kib": children.ru_maxrss, "logical_storage_bytes_before_final_reports": sum(
                      path.stat().st_size for path in files), "inference_tokens": None, "money_usd": None,
                  "consumer_executed": False, "application_qualified": False,
                  "scope": "Ten-package component environment with original FastAPI import bridge; Alpha app not imported"}
        write_json(self.out / "preparation.json", result)
        write_json(self.out / "licenses/index.json", self.wheels)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--metadata-reuse", type=Path, action="append", default=[])
    parser.add_argument("--wheel-reuse", type=Path, action="append", default=[])
    parser.add_argument("--confirmation-freeze", type=Path)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    result = Preparation(args).run()
    print(json.dumps({key: result[key] for key in ("environment_id", "complete", "error", "network_requests",
                                                  "network_response_bytes", "wall_seconds", "child_cpu_seconds")}))
    if not result["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

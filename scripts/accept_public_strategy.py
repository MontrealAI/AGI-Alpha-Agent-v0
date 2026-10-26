# SPDX-License-Identifier: Apache-2.0
"""Install actual public release bodies after publication; never publish or retry."""

from __future__ import annotations

import argparse
import base64
from configparser import ConfigParser
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import tomllib
from typing import Any
from urllib.request import Request, urlopen
import zipfile

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

from scripts import strategy_engineering_release as checks

REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"
API = "https://api.github.com/repos/" + REPOSITORY
QA_FILES = ("test_integration.py", "test_browser.py", "test_crash.py", "proc_namespace.py")
MAX_JUNIT_BYTES = 8 * 1024 * 1024
SAFE_JSON = (
    "integrated-journey.json",
    "integrated-summary.json",
    "service-only-journey.json",
    "service-only-summary.json",
    "service-only-export.json",
    "browser-acceptance.json",
    "browser-mission-export.json",
    "browser-kept-methods.json",
    "browser-mobile-layout.json",
    "browser-prepared-input-default.json",
    "browser-prepared-input-optin.json",
    "crash-recovery.json",
)


class _EntryPoints(ConfigParser):
    """Preserve case-sensitive executable names when comparing committed metadata."""

    def optionxform(self, optionstr: str) -> str:
        """Retain the actual entry-point spelling."""
        return optionstr


def require(condition: bool, message: str) -> None:
    """Refuse an unknown source, body or environment without an alternate path."""
    if not condition:
        raise ValueError(message)


def sha(data: bytes) -> str:
    """Return the complete byte identity."""
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Write a local receipt, never an authority grant."""
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def stage_public_planning_preparer(repo: Path, commit: str, destination: Path) -> dict[str, str]:
    """Copy exact committed public HTML for local-file QA, never from the worktree."""
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "Exact public-preparer source commit is required")
    name = "docs/try/index.html"
    raw = subprocess.check_output(["git", "-C", str(repo), "show", "--no-textconv", commit + ":" + name])
    destination.write_bytes(raw)
    return {"commit": commit, "path": name, "sha256": sha(raw), "scope": checks.PUBLIC_PREPARER_SCOPE}


def public_json(url: str) -> dict[str, Any]:
    """Read bounded public GitHub metadata without credentials or retries."""
    require(url.startswith(API + "/"), "Unexpected metadata endpoint")
    with urlopen(Request(url, headers={"User-Agent": "Alpha-public-install-acceptance"}), timeout=60) as response:
        data = response.read(5_000_001)
    require(len(data) <= 5_000_000, "Public metadata exceeds its bound")
    return checks._json(data)


def release_identity(version: str, commit: str) -> dict[str, Any]:
    """Bind normal public visibility and its annotated tag to the accepted source."""
    value = public_json(API + "/releases/tags/v" + version)
    require(
        value.get("tag_name") == "v" + version
        and bool(value.get("published_at"))
        and value.get("draft") is False
        and value.get("prerelease") is False,
        "Release is not normally public",
    )
    target = public_json(API + "/git/ref/tags/v" + version)["object"]
    for _ in range(4):
        if target.get("type") != "tag":
            break
        require(re.fullmatch(r"[0-9a-f]{40}", target.get("sha", "")) is not None, "Invalid public tag object")
        target = public_json(API + "/git/tags/" + target["sha"])["object"]
    require(target.get("type") == "commit" and target.get("sha") == commit, "Public tag has another source")
    names = [row.get("name") for row in value["assets"]]
    require(len(names) == len(set(names)), "Duplicate public asset")
    return value


def fetch_asset(release: dict[str, Any], name: str, destination: Path) -> dict[str, Any]:
    """Download one fixed public body and require its complete published identity."""
    rows = [row for row in release["assets"] if row.get("name") == name]
    require(len(rows) == 1, "Required public asset is missing: " + name)
    row = rows[0]
    require(
        type(row.get("size")) is int
        and 0 < row["size"] <= 50_000_000
        and re.fullmatch(r"sha256:[0-9a-f]{64}", row.get("digest", "")) is not None,
        "Public asset lacks bounded size/hash",
    )
    expected_url = f"https://github.com/{REPOSITORY}/releases/download/{release['tag_name']}/{name}"
    require(row.get("browser_download_url") == expected_url, "Public asset URL escaped the fixed release")
    require(not destination.exists(), "Asset destination already exists; no overwrite or retry")
    started, total, digest = time.perf_counter(), 0, hashlib.sha256()
    with urlopen(
        Request(expected_url, headers={"User-Agent": "Alpha-public-install-acceptance"}), timeout=60
    ) as response:
        require(response.status == 200, "Public body did not return HTTP200")
        with destination.open("xb") as stream:
            while block := response.read(1024 * 1024):
                total += len(block)
                require(total <= row["size"] and time.perf_counter() - started <= 180, "Public body exceeded its bound")
                digest.update(block)
                stream.write(block)
    require(total == row["size"] and digest.hexdigest() == row["digest"][7:], "Public body size/hash mismatch")
    return {"name": name, "asset_id": row["id"], "bytes": total, "sha256": digest.hexdigest(), "http": 200}


def checksum_list(raw: bytes) -> dict[str, str]:
    """Refuse duplicate, escaping or malformed public checksum rows."""
    result: dict[str, str] = {}
    for line in raw.decode().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64}) [ *]([^/\\]+)", line)
        require(match is not None and match[2] not in result, "Malformed public checksum list")
        assert match is not None
        require(match[2] not in {".", ".."}, "Escaping checksum name")
        result[match[2]] = match[1]
    return result


def verify_environment(report: dict[str, Any], prefix: Path, version: str, companion: bool = False) -> None:
    """Require actual isolated installation origins, not a checkout or shared site."""
    require(
        report.get("version") == version and report.get("system_site_packages") is False,
        "Wrong runtime or dirty virtual environment",
    )
    require(Path(report.get("prefix", "")).absolute() == prefix.absolute(), "Unexpected interpreter prefix")
    require(Path(report.get("module", "")).resolve().is_relative_to(prefix.resolve()), "Source-shadowed runtime")
    if companion:
        require(
            Path(report.get("companion", "")).resolve().is_relative_to(prefix.resolve()), "Source-shadowed companion"
        )


def core_payload(repo: Path, commit: str, wheel: Path, installed: Path | None = None) -> dict[str, Any]:
    """Bind all executable/data payload to Git and installed bytes to the public wheel."""
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "Core source must be an exact accepted commit")
    resolved = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--verify", commit + "^{commit}"])
    require(resolved.decode().strip() == commit, "Core source does not identify that exact accepted commit")
    listing = subprocess.check_output(["git", "-C", str(repo), "ls-tree", "-rz", commit])
    blobs: dict[str, str] = {}
    for item in listing.split(b"\0"):
        if item:
            meta, byte_name = item.split(b"\t", 1)
            mode, kind, identity = meta.decode().split()
            if kind == "blob" and mode in {"100644", "100755"}:
                require(re.fullmatch(r"[0-9a-f]{40}", identity) is not None, "Invalid accepted Git blob metadata")
                blobs[byte_name.decode()] = identity
    rows, python_files = [], 0
    project_raw = subprocess.check_output(["git", "-C", str(repo), "show", "--no-textconv", commit + ":pyproject.toml"])
    project = tomllib.loads(project_raw.decode())["project"]
    metadata_prefix = wheel.name[: -len("-py3-none-any.whl")] + ".dist-info/"
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        require(
            len(names) == len(set(names)) and sum(i.file_size for i in archive.infolist()) <= 100_000_000,
            "Unbounded or duplicate core wheel",
        )
        for info in archive.infolist():
            name = info.filename
            require(
                not name.startswith("/")
                and "\\" not in name
                and ".." not in name.split("/")
                and (info.external_attr >> 16) & 0o170000 != 0o120000,
                "Unsafe core wheel path",
            )
            require(
                name.startswith(
                    (
                        "alpha_factory_v1/",
                        "af_requests/",
                        "openai_agents/",
                        metadata_prefix,
                    )
                ),
                "Unexpected core wheel top-level payload",
            )
            if info.is_dir() or name.endswith(".dist-info/RECORD"):
                continue
            raw = archive.read(info)
            if not name.startswith(metadata_prefix):
                accepted_identity = blobs.get(name)
                require(accepted_identity is not None, "Core package body differs from accepted Git source")
                assert accepted_identity is not None
                accepted = subprocess.check_output(["git", "-C", str(repo), "cat-file", "blob", accepted_identity])
                require(
                    accepted == raw,
                    "Core package body differs from accepted Git source",
                )
            if name.endswith(".py"):
                python_files += 1
            if installed is not None:
                path = installed / name
                require(
                    path.is_file()
                    and not path.is_symlink()
                    and path.resolve().is_relative_to(installed.resolve())
                    and path.read_bytes() == raw,
                    "Installed core payload differs from actual public wheel",
                )
            rows.append({"path": name, "bytes": len(raw), "sha256": sha(raw)})
        metadata = BytesParser().parsebytes(archive.read(metadata_prefix + "METADATA"))
        require(
            metadata["Name"] == project["name"] and metadata["Version"] == project["version"],
            "Core distribution metadata differs from committed source",
        )
        entries = _EntryPoints()
        entries.read_string(archive.read(metadata_prefix + "entry_points.txt").decode())
        require(
            entries.sections() == ["console_scripts"] and dict(entries["console_scripts"]) == project["scripts"],
            "Core executable entry points differ from committed source",
        )
    require(python_files > 0, "Public core wheel omitted its Python source")
    return {"python_files": python_files, "payload_members": len(rows), "inventory_sha256": checks._digest(rows)}


def verify_junit(path: Path) -> None:
    """Require bounded regular JUnit evidence without DTDs, entities or external references."""
    absolute = path.absolute()
    require(len(absolute.parts) > 1 and ".." not in absolute.parts, "Invalid JUnit artifact path")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        directory = os.open(absolute.anchor, directory_flags)
        try:
            for part in absolute.parts[1:-1]:
                next_directory = os.open(part, directory_flags, dir_fd=directory)
                os.close(directory)
                directory = next_directory
            descriptor = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                require(
                    stat.S_ISREG(info.st_mode) and info.st_size <= MAX_JUNIT_BYTES,
                    "JUnit artifact must be a bounded regular file",
                )
                raw = stream.read(MAX_JUNIT_BYTES + 1)
        finally:
            os.close(directory)
    except OSError as error:
        raise ValueError("JUnit artifact must have regular non-symlink ancestors and file") from error
    require(len(raw) <= MAX_JUNIT_BYTES, "JUnit artifact grew beyond its bound")
    try:
        xml = SafeET.fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (DefusedXmlException, SyntaxError) as error:
        raise ValueError("Unsafe or malformed JUnit XML") from error
    require(
        bool(list(xml.iter("testcase"))) and not any(list(xml.iter(key)) for key in ("failure", "error", "skipped")),
        "Installed acceptance failed, skipped or omitted a case",
    )


def safe_artifacts(work: Path, evidence: Path, summary: dict[str, Any]) -> None:
    """Retain complete sanitized failures, never private homes, credentials, HAR or images."""
    secrets: set[bytes] = set()
    for name in ("api.token", "identity.key"):
        for path in work.rglob(name):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
                continue
            data = path.read_bytes()
            if name == "api.token":
                data = data.strip()
            if data:
                rendered = repr(data)
                secrets.update(
                    (
                        data,
                        data.hex().encode(),
                        data.hex().upper().encode(),
                        rendered.encode(),
                        rendered[2:-1].encode(),
                        json.dumps(rendered).encode(),
                        json.dumps(rendered)[1:-1].encode(),
                        base64.b64encode(data),
                        base64.urlsafe_b64encode(data),
                        base64.b64encode(data).rstrip(b"="),
                        base64.urlsafe_b64encode(data).rstrip(b"="),
                    )
                )
    for path in sorted((work / "logs").glob("*")):
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 20_000_000:
            continue
        raw = path.read_bytes()
        clean = raw
        for secret in sorted(secrets, key=len, reverse=True):
            clean = clean.replace(secret, b"[REDACTED_EPHEMERAL_TEST_CREDENTIAL]")
        clean = re.sub(rb"(https?://)[^\s/@]+:[^\s/@]+@", rb"\1[REDACTED]@", clean)
        clean = re.sub(rb"(?i)(Bearer\s+)[A-Za-z0-9._~-]{12,}", rb"\1[REDACTED]", clean)
        clean = clean.replace(str(work).encode(), b"WORK_ROOT")
        (evidence / path.name).write_bytes(clean)
    outputs = work / "public-results"
    for name in SAFE_JSON:
        path = outputs / name
        if not path.exists():
            continue
        try:
            raw = checks._read(path)
            require(not any(secret in raw for secret in secrets), "Sensitive output")
            checks._empty_authority(checks._json(raw))
        except (ValueError, OSError, json.JSONDecodeError):
            raw = (
                path.read_bytes()
                if path.is_file() and not path.is_symlink() and path.stat().st_size <= 5_000_000
                else b""
            )
            summary.setdefault("withheld_sensitive_outputs", []).append(
                {"name": name, "bytes": len(raw), "sha256": sha(raw)}
            )
            summary["state"] = "FAILED_NOT_QUALIFIED"
            continue
        (evidence / name).write_bytes(raw)
    write_json(evidence / "public-installation.json", summary)


def accept(repo: Path, commit: str, work: Path, evidence: Path) -> None:
    """Perform this fixed postpublication installation and the existing installed QA."""
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "Exact source commit is required")
    actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    require(actual == commit, "Checkout source differs from GITHUB_SHA")
    require(
        work.is_absolute() and not work.exists() and not work.resolve().is_relative_to(repo.resolve()),
        "Acceptance requires a new outside-checkout root",
    )
    require(
        not evidence.exists() and evidence.resolve().is_relative_to((repo / "evidence").resolve()),
        "Use a fresh artifact-only evidence directory",
    )
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    for name in ("logs", "core-assets", "companion-assets", "runtime-assets", "public-results", "qa", "tmp", "home"):
        (work / name).mkdir()
    summary: dict[str, Any] = {
        "schema": "strategy-public-installed/v1",
        "commit": commit,
        "state": "RUNNING_NOT_QUALIFIED",
        "commands": [],
        "downloads": [],
        "production_authority": False,
        "four_product_installation": False,
        "unknown_costs": ["human effort", "whole QA/development cost", "device/monetary cost"],
        "held_harness_fleet_decisions": "unchanged",
    }
    stage = "public-identities"
    env = {
        key: os.environ[key]
        for key in (
            "PATH",
            "LANG",
            "LC_ALL",
            "HTTPS_PROXY",
            "HTTP_PROXY",
            "NO_PROXY",
            "SSL_CERT_FILE",
            "REQUESTS_CA_BUNDLE",
        )
        if key in os.environ
    }
    env.update(
        HOME=str(work / "home"),
        TMPDIR=str(work / "tmp"),
        PYTHONNOUSERSITE="1",
        PYTHONDONTWRITEBYTECODE="1",
        PIP_NO_CACHE_DIR="1",
        PIP_DISABLE_PIP_VERSION_CHECK="1",
    )

    def run(label: str, command: list[str], cwd: Path | None = None, extra: dict[str, str] | None = None) -> bytes:
        nonlocal stage
        stage = label
        started = time.perf_counter()
        result = subprocess.run(command, cwd=cwd or work, env={**env, **(extra or {})}, capture_output=True)
        raw = result.stdout + result.stderr
        (work / "logs" / (label + ".log")).write_bytes(raw)
        summary["commands"].append(
            {
                "label": label,
                "exit": result.returncode,
                "elapsed_seconds": time.perf_counter() - started,
                "raw_log_bytes": len(raw),
                "raw_log_sha256": sha(raw),
            }
        )
        require(result.returncode == 0, "Command failed without retry: " + label)
        return result.stdout

    try:
        project_raw = subprocess.check_output(
            ["git", "-C", str(repo), "show", "--no-textconv", commit + ":pyproject.toml"]
        )
        version = tomllib.loads(project_raw.decode())["project"]["version"]
        require(
            re.fullmatch(r"\d+\.\d+\.\d+", version) is not None and tuple(map(int, version.split("."))) >= (1, 44, 0),
            "No public Strategy profile in this core version",
        )
        files = checks._committed_files(repo, commit)
        project = tomllib.loads(files[checks.CONTRIB + "pyproject.toml"].decode())["project"]
        companion = project["version"]
        require(re.fullmatch(r"[0-9A-Za-z.]+", companion) is not None, "Invalid fixed companion version")
        release = release_identity(version, commit)
        runtime = public_json(API + "/releases/tags/v1.42.0")
        require(runtime.get("draft") is False and bool(runtime.get("published_at")), "Preserved runtime is unavailable")
        core_names = (
            "install_agent.py",
            f"alpha_factory_v1-{version}-py3-none-any.whl",
            "requirements-agent.lock",
            "SHA256SUMS",
        )
        companion_names = (
            f"{checks.DIST}-{companion}-py3-none-any.whl",
            f"strategy-succession-{companion}-operator.md",
            f"strategy-succession-{companion}-compatibility.json",
        )
        for names, current, directory in (
            (core_names, release, "core-assets"),
            (companion_names, release, "companion-assets"),
            (("alpha_factory_v1-1.42.0-py3-none-any.whl", "SHA256SUMS"), runtime, "runtime-assets"),
        ):
            for name in names:
                stage = "download:" + name
                attempt: dict[str, Any] = {"name": name, "status": "FAILED_NOT_QUALIFIED", "attempt": 1}
                summary["downloads"].append(attempt)
                started = time.perf_counter()
                try:
                    attempt.update(fetch_asset(current, name, work / directory / name), status="PASS")
                finally:
                    attempt["elapsed_seconds"] = time.perf_counter() - started
        sums = checksum_list((work / "core-assets/SHA256SUMS").read_bytes())
        old_sums = checksum_list((work / "runtime-assets/SHA256SUMS").read_bytes())
        for directory, expected in (("core-assets", sums), ("companion-assets", sums), ("runtime-assets", old_sums)):
            for path in (work / directory).iterdir():
                if path.name != "SHA256SUMS":
                    require(expected.get(path.name) == sha(path.read_bytes()), "Published checksum-list mismatch")
        wheel = work / "companion-assets" / companion_names[0]
        inspected = checks._verify_wheel(wheel.read_bytes(), files)
        profile, source = inspected["profile"], inspected["source_hash"]
        compat = checks._read_json(work / "companion-assets" / companion_names[2])
        require(
            compat.get("schema") == "strategy-engineering-release-compatibility/v1"
            and compat.get("core_source_commit") == commit
            and compat.get("core_distribution_version") == version
            and compat.get("companion_version") == companion
            and compat.get("source_hash") == source
            and compat.get("runtime_version") == "1.42.0"
            and compat.get("runtime_public_wheel_sha256") == checks.PUBLIC_RUNTIME
            and compat.get("qualified_environment") == profile["qualified_environment"]
            and compat.get("wheel")
            == {"name": wheel.name, "sha256": sha(wheel.read_bytes()), "bytes": wheel.stat().st_size}
            and compat.get("production_authority") is False
            and compat.get("four_product_installation") is False,
            "Public compatibility descriptor has another source/runtime",
        )
        require(
            (work / "companion-assets" / companion_names[1]).read_bytes() == files[checks.CONTRIB + "docs/operator.md"],
            "Public operator guide differs from committed bytes",
        )
        runtime_wheel = work / "runtime-assets/alpha_factory_v1-1.42.0-py3-none-any.whl"
        require(sha(runtime_wheel.read_bytes()) == checks.PUBLIC_RUNTIME, "Preserved runtime wheel differs")
        for source_path, public_path in (
            ("scripts/install_agent.py", "install_agent.py"),
            ("requirements-agent.lock", "requirements-agent.lock"),
        ):
            committed = subprocess.check_output(
                ["git", "-C", str(repo), "show", "--no-textconv", commit + ":" + source_path]
            )
            require(
                (work / "core-assets" / public_path).read_bytes() == committed,
                "Core installer/lock differs from accepted source",
            )
        core_wheel = work / "core-assets" / core_names[1]
        core_payload(repo, commit, core_wheel)
        core_env, companion_env = work / "core-env", work / "companion-env"
        run(
            "core-check",
            [
                sys.executable,
                str(work / "core-assets/install_agent.py"),
                "--release-dir",
                str(work / "core-assets"),
                "--venv",
                str(core_env),
                "--check-only",
            ],
        )
        run(
            "core-install",
            [
                sys.executable,
                str(work / "core-assets/install_agent.py"),
                "--release-dir",
                str(work / "core-assets"),
                "--venv",
                str(core_env),
            ],
        )
        run("companion-venv", [sys.executable, "-m", "venv", str(companion_env)])
        py = str(companion_env / "bin/python")
        run("companion-install", [py, "-m", "pip", "install", str(runtime_wheel), str(wheel)])
        run("qa-tools", [py, "-m", "pip", "install", "pytest==8.4.2", "playwright==1.64.1", "defusedxml==0.7.1"])
        run("companion-pip-check", [py, "-I", "-m", "pip", "check"])
        probe = (
            "import json,sys,pathlib,alpha_factory_v1 as a;"
            "p=pathlib.Path(sys.prefix);v={'version':a.__version__,'prefix':str(p),'module':a.__file__,"
            "'system_site_packages':'include-system-site-packages = true' in (p/'pyvenv.cfg').read_text()};"
        )
        core_report = json.loads(
            run("core-origin", [str(core_env / "bin/python"), "-I", "-c", probe + "print(json.dumps(v))"])
        )
        verify_environment(core_report, core_env, version)
        summary["core_source_wheel_installed"] = core_payload(
            repo, commit, core_wheel, core_env / "lib/python3.12/site-packages"
        )
        report = json.loads(
            run(
                "companion-origin",
                [
                    py,
                    "-I",
                    "-c",
                    probe
                    + "import strategy_succession_engineering.serve as s;v['companion']=str(s.ROOT);print(json.dumps(v))",
                ],
            )
        )
        verify_environment(report, companion_env, "1.42.0", companion=True)
        payload_probe = (
            "import pathlib,zipfile,hashlib,json;import strategy_succession_engineering.serve as s;rows=[];"
            "z=zipfile.ZipFile(__import__('sys').argv[1]);"
            "\nfor n in z.namelist():"
            "\n if n.startswith('strategy_succession_engineering/') and not n.endswith('/'):"
            "\n  b=z.read(n);assert (s.ROOT/n.removeprefix('strategy_succession_engineering/')).read_bytes()==b;"
            "rows.append({'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})"
            "\nprint(json.dumps(rows))"
        )
        installed_rows = json.loads(run("companion-payload", [py, "-I", "-c", payload_probe, str(wheel)]))
        summary["companion_installed_payload"] = {
            "members": len(installed_rows),
            "inventory_sha256": checks._digest(installed_rows),
        }
        for name in QA_FILES:
            qa_path = "contrib/strategy_succession/qa/" + name
            raw = subprocess.check_output(["git", "-C", str(repo), "show", "--no-textconv", commit + ":" + qa_path])
            (work / "qa" / name).write_bytes(raw)
        summary["public_preparer_source"] = stage_public_planning_preparer(
            repo, commit, work / "qa" / "public-planning-preparer.html"
        )
        run("chromium", [py, "-m", "playwright", "install", "--with-deps", "chromium"])
        test_env = {"STRATEGY_INSTALLED_ACCEPTANCE": "1", "STRATEGY_EVIDENCE_DIR": str(work / "public-results")}
        for name, test in (("api", "integration"), ("browser", "browser"), ("crash", "crash")):
            run(
                name,
                [
                    py,
                    "-I",
                    "-m",
                    "pytest",
                    "--noconftest",
                    "-o",
                    "addopts=",
                    "-q",
                    "--basetemp",
                    str(work / ("private-" + name)),
                    "test_" + test + ".py",
                    "--junitxml=" + str(work / "logs" / (name + ".xml")),
                ],
                cwd=work / "qa",
                extra=test_env,
            )
            verify_junit(work / "logs" / (name + ".xml"))
        stage = "validate-executed-records"
        output = work / "public-results"
        plan = checks._read_json(output / "integrated-journey.json")
        checks._verify_plan(plan, source, profile)
        service_only = checks._verify_service_only(
            checks._read_json(output / "service-only-journey.json"),
            checks._read_json(output / "service-only-summary.json"),
            checks._read(output / "service-only-export.json"),
            plan,
            source,
            profile,
        )
        summary["service_only_control"] = {
            "plan_id": service_only["plan_id"],
            "outcome_hash": service_only["outcome_hash"],
            "costs": service_only["outcome"]["costs"],
            "qualification": "Matched construction-off API control; no causal speedup or monetary payback claim",
        }
        checks._verify_child_environment(
            checks._read_json(output / "integrated-summary.json")["child_environment"], profile
        )
        browser_report = checks._read_json(output / "browser-acceptance.json")
        browser_plan = checks._verify_browser(
            browser_report,
            checks._read(output / "browser-mission-export.json"),
            source,
            profile,
        )
        checks._verify_public_preparer(
            browser_report,
            browser_plan,
            checks._read(output / "browser-prepared-input-default.json"),
            checks._read(output / "browser-prepared-input-optin.json"),
            checks._read(work / "qa" / "public-planning-preparer.html"),
        )
        crash = checks._verify_crash(checks._read_json(output / "crash-recovery.json"), source, profile)
        after = release_identity(version, commit)
        require(
            sorted((a["id"], a["name"], a["size"], a["digest"]) for a in after["assets"])
            == sorted((a["id"], a["name"], a["size"], a["digest"]) for a in release["assets"]),
            "Public asset inventory changed during acceptance",
        )
        summary.update(
            state="PASS",
            core_version=version,
            companion_version=companion,
            runtime_version="1.42.0",
            source_hash=source,
            release_id=release["id"],
            public_companion_sha256=sha(wheel.read_bytes()),
            costs={
                "api": plan["outcome"]["costs"],
                "browser": browser_plan["outcome"]["costs"],
                "crash_observed": crash["observed"],
                "crash_unknown_reservation": crash["caps"],
            },
            foreground_only=True,
            actual_public_package=True,
            actual_browser=True,
        )
    except BaseException as error:
        summary.update(
            state="FAILED_NOT_QUALIFIED",
            failed_stage=stage,
            error_type=type(error).__name__,
            automatic_retry=False,
            public_release_changed=False,
        )
        raise
    finally:
        safe_artifacts(work, evidence, summary)
        if summary["state"] == "FAILED_NOT_QUALIFIED":
            print("Postpublication installation is UNQUALIFIED; public assets remain unchanged.")
    require(summary["state"] == "PASS", "Sanitized artifact checks refused acceptance")


def main() -> None:
    """Run only in the existing normal-main publication lineage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    require(
        os.environ.get("GITHUB_REPOSITORY") == REPOSITORY
        and os.environ.get("GITHUB_REF") == "refs/heads/main"
        and os.environ.get("GITHUB_SHA") == args.commit,
        "Public installed acceptance is restricted to normal main",
    )
    accept(Path(__file__).resolve().parents[1], args.commit, args.root, args.evidence)


if __name__ == "__main__":
    main()

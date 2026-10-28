#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate shared legacy Docker build contexts and optional Compose models."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request

import yaml

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def _credentials() -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                value
                for name, value in os.environ.items()
                if value
                and any(
                    part in name.upper()
                    for part in ("TOKEN", "PASSWORD", "SECRET", "CREDENTIAL", "PRIVATE_KEY", "API_KEY")
                )
            },
            key=len,
            reverse=True,
        )
    )


def _redact(text: str, credentials: tuple[str, ...]) -> str:
    """Exclude known operator credentials even from unexpected client output."""
    if not credentials:
        return text
    matches = re.compile("(?=(" + "|".join(re.escape(value) for value in credentials) + "))")
    pieces: list[str] = []
    position = 0
    for match in matches.finditer(text):
        if match.start() >= position:
            pieces.extend((text[position : match.start()], "[REDACTED]"))
        position = max(position, match.start() + len(match.group(1)))
    pieces.append(text[position:])
    return "".join(pieces)


def _redact_values(value: object, credentials: tuple[str, ...]) -> object:
    """Mask decoded strings, including object keys, while preserving typed state."""
    if isinstance(value, str):
        return _redact(value, credentials)
    if isinstance(value, dict):
        return {
            _redact(name, credentials) if isinstance(name, str) else name: _redact_values(item, credentials)
            for name, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_values(item, credentials) for item in value]
    return value


def _masked_tail(raw: bytes, patterns: list[bytes], head_truncated: bool, limit: int) -> bytes:
    """Mask overlapping credentials and unsafe capture/EOF boundaries before trimming."""
    spans: list[tuple[int, int]] = []
    if patterns:
        matcher = re.compile(b"(?=(" + b"|".join(re.escape(value) for value in patterns) + b"))")
        spans.extend((match.start(), match.start() + len(match.group(1))) for match in matcher.finditer(raw))
        if head_truncated:
            # Any unobserved credential prefix can affect only this overlap.
            spans.append((0, max(map(len, patterns)) - 1))
        partial = max(
            (
                width
                for value in patterns
                for width in range(1, min(len(raw), len(value) - 1) + 1)
                if raw.endswith(value[:width])
            ),
            default=0,
        )
        if partial:
            spans.append((len(raw) - partial, len(raw)))
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    result = bytearray()
    position = 0
    for start, end in merged:
        result.extend(raw[position:start])
        result.extend(b"[REDACTED]")
        del result[:-limit]
        position = end
    result.extend(raw[position:])
    return bytes(result[-limit:])


def _diagnostic_command(command: list[str], env: dict[str, str], timeout: float = 8) -> dict[str, object]:
    """Drain a diagnostic into a bounded tail; reserve two seconds for termination."""
    if not 0 < timeout <= 8:
        raise ValueError("diagnostic execution budget must be at most eight seconds")
    limit = 16_384
    capture_limit = 2 * limit
    tail = bytearray()
    credentials = _credentials()
    patterns = sorted(
        {
            variant.encode("utf-8")
            for value in credentials
            for variant in (value, json.dumps(value)[1:-1], json.dumps(value, ensure_ascii=False)[1:-1])
        },
        key=len,
        reverse=True,
    )
    withheld = sum(map(len, patterns)) > limit
    total = 0
    expired = False
    abnormal = False
    process = subprocess.Popen(
        command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True
    )
    assert process.stdout is not None
    deadline = time.monotonic() + timeout
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    expired = True
                    break
                for selected, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(selected.fd, 4096)
                    if not chunk:
                        selector.unregister(selected.fileobj)
                        continue
                    total += len(chunk)
                    if not withheld:
                        tail.extend(chunk)
                        del tail[:-capture_limit]
        if not expired:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                expired = True
    except BaseException:
        abnormal = True
        raise
    finally:
        try:
            try:
                if abnormal or expired or process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    finally:
                        process.wait(timeout=2)
            finally:
                process.stdout.close()
        except BaseException:
            if not abnormal:
                raise
    if withheld:
        text = b""
    else:
        text = _masked_tail(bytes(tail), patterns, total > capture_limit, limit)
        if total <= capture_limit:
            try:
                decoded = json.loads(tail)
            except (UnicodeError, ValueError):
                pass
            else:
                text = json.dumps(_redact_values(decoded, credentials), ensure_ascii=False).encode("utf-8")
                if len(text) > limit:
                    withheld = True
                    text = b""
        text = text.decode("utf-8", errors="replace").encode("utf-8")
    return {
        "status": "output-withheld"
        if withheld
        else "timed-out"
        if expired
        else "ok"
        if process.returncode == 0
        else "command-failed",
        "returncode": process.returncode,
        "truncated": total > limit or len(text) > limit,
        "tail": text[-limit:].decode("utf-8", errors="ignore"),
    }


def _dev_ui_failure(root: Path, command: list[str], env: dict[str, str], error: Exception, output: Path | None) -> None:
    """Preserve bounded diagnostics before cleanup; never replace acceptance failure."""
    report: dict[str, object] = {
        "schema": "agialpha.legacy-dev-ui-failure.v1",
        "passed": False,
        "error_type": type(error).__name__,
        "startup_returncode": error.returncode if isinstance(error, subprocess.CalledProcessError) else None,
    }
    for name, args in (
        ("ui_logs", command + ["logs", "--no-color", "--timestamps", "--tail", "100", "ui"]),
        (
            "container_state",
            ["docker", "inspect", "--type", "container", "--format", "{{json .State}}", "alpha-dev-ui-acceptance"],
        ),
    ):
        try:
            captured = _diagnostic_command(args, env)
            if name == "container_state":
                # Never record an unfiltered inspect result, Config or environment.
                text = str(captured.pop("tail"))
                raw = _redact_values(json.loads(text), _credentials()) if captured["status"] == "ok" else {}
                if not isinstance(raw, dict):
                    raise ValueError("diagnostic State must be an object")
                fields = (
                    "Status",
                    "Running",
                    "Restarting",
                    "OOMKilled",
                    "ExitCode",
                    "Error",
                    "StartedAt",
                    "FinishedAt",
                )
                captured["state"] = {field: raw[field] for field in fields if field in raw}
                health = raw.get("Health", {})
                captured["health"] = {field: health[field] for field in ("Status", "FailingStreak") if field in health}
                captured["health_log"] = [
                    {field: row[field] for field in ("Start", "End", "ExitCode", "Output") if field in row}
                    for row in health.get("Log", [])[-3:]
                ]
            report[name] = captured
        except Exception as exc:
            report[name] = {"status": "diagnostic-failed", "error_type": type(exc).__name__}
    try:
        report["disk_bytes"] = dict(zip(("total", "used", "free"), shutil.disk_usage(root)))
    except OSError as exc:
        report["disk_bytes"] = {"status": "diagnostic-failed", "error_type": type(exc).__name__}
    encoded = json.dumps(report, indent=2) + "\n"
    print(encoded, file=sys.stderr)
    if output is not None:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(encoded)
        except OSError as exc:
            print("Development UI diagnostics could not be saved: " + type(exc).__name__, file=sys.stderr)


def validate_dev_ui(root: Path, failure_output: Path | None = None) -> None:
    """Start the real development UI with clean volumes and resolve its shared module."""
    source = root / "alpha_factory_v1/docker-compose.override.yml"
    model = yaml.safe_load(source.read_text())
    service = model["services"]["ui"]
    service["container_name"] = "alpha-dev-ui-acceptance"
    service["ports"] = ["127.0.0.1:3000:3000"]
    service["healthcheck"]["interval"] = "2s"
    service["volumes"] = [
        (
            str((source.parent / mount.split(":", 1)[0]).resolve()) + ":" + mount.split(":", 1)[1]
            if mount.startswith("./")
            else mount
        )
        for mount in service["volumes"]
    ]
    fixture = {"services": {"ui": service}, "networks": model["networks"], "volumes": {"ui-node-modules": {}}}
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "HOME", "SYSTEMROOT", "TMPDIR"}}
    env["COMPOSE_DISABLE_ENV_FILE"] = "1"
    with tempfile.TemporaryDirectory(prefix="alpha-dev-ui-") as temporary:
        compose = Path(temporary) / "compose.yml"
        compose.write_text(yaml.safe_dump(fixture))
        command = ["docker", "compose", "--env-file", os.devnull, "-p", "alpha-dev-ui-acceptance", "-f", str(compose)]
        try:
            subprocess.run(command + ["up", "-d", "--wait", "--wait-timeout", "240"], env=env, check=True, timeout=360)
            for route, expected in (
                ("/src/Telemetry.ts", "initTelemetry"),
                ("/@fs/ui/alpha_factory_v1/core/telemetry.js", "function initTelemetry"),
            ):
                with urllib.request.urlopen("http://127.0.0.1:3000" + route, timeout=15) as response:
                    document = response.read().decode()
                    if response.status != 200 or expected not in document:
                        raise ValueError(f"Development UI module did not load: {route}")
        except Exception as exc:
            try:
                _dev_ui_failure(root, command, env, exc, failure_output)
            except Exception as diagnostic_error:
                print("Development UI diagnostics failed: " + type(diagnostic_error).__name__, file=sys.stderr)
            raise
        finally:
            original_failure = sys.exc_info()[0] is not None
            try:
                subprocess.run(command + ["down", "--volumes", "--remove-orphans"], env=env, check=True, timeout=60)
            except Exception as cleanup_error:
                if not original_failure:
                    raise
                print("Development UI cleanup failed: " + type(cleanup_error).__name__, file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker-compose", action="store_true", help="Require real Compose config validation")
    parser.add_argument("--dev-ui", action="store_true", help="Start and verify the isolated development UI")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    shared = root / "alpha_factory_v1/Dockerfile"
    tracked = (
        subprocess.check_output(["git", "ls-files", "-z", "--", "*compose*.yml", "*compose*.yaml"], cwd=root)
        .decode()
        .split("\0")
    )
    consumers: list[dict[str, str]] = []
    configurations: set[Path] = set()
    for name in sorted(filter(None, tracked)):
        path = root / name
        model = yaml.safe_load(path.read_text())
        for service, settings in model.get("services", {}).items():
            if not isinstance(settings, dict):
                raise ValueError(f"{name}: service {service} must be an object")
            build = settings.get("build")
            if not isinstance(build, dict):
                continue
            context = (path.parent / build.get("context", ".")).resolve()
            dockerfile = (context / build.get("dockerfile", "Dockerfile")).resolve()
            if not dockerfile.is_file():
                raise ValueError(f"{name}: {service} Dockerfile does not exist: {dockerfile}")
            if dockerfile != shared:
                continue
            # Resolve every local COPY input, including globs, against the
            # consumer's actual context. Stage-to-stage COPY has no host input.
            for line in shared.read_text().splitlines():
                if not line.startswith("COPY ") or "--from=" in line:
                    continue
                for source in shlex.split(line)[1:-1]:
                    if not list(context.glob(source)):
                        raise ValueError(f"{name}: {service} COPY input {source!r} is absent from {context}")
            configurations.add(path)
            consumers.append({"file": name, "service": service, "context": str(context.relative_to(root))})
    # MuZero has a dedicated locked image and its own mandatory Docker/browser
    # acceptance job. Verify the identities of the remaining shared consumers;
    # a count alone could hide an accidentally disconnected configuration.
    expected = {
        ("alpha_factory_v1/docker-compose.yml", "orchestrator"),
        ("alpha_factory_v1/docker-compose.override.yml", "orchestrator"),
        ("alpha_factory_v1/demos/aiga_meta_evolution/docker-compose.aiga.yml", "orchestrator"),
        ("alpha_factory_v1/demos/era_of_experience/docker-compose.experience.yml", "orchestrator"),
        ("alpha_factory_v1/demos/macro_sentinel/docker-compose.macro.yml", "orchestrator"),
        ("alpha_factory_v1/demos/self_healing_repo/docker-compose.selfheal.yml", "orchestrator"),
    }
    missing = expected - {(consumer["file"], consumer["service"]) for consumer in consumers}
    if missing:
        raise ValueError(f"missing shared Dockerfile consumers: {sorted(missing)}")
    if args.docker_compose:
        # Parse only: never start services, pull images or load operator secrets.
        env = {key: value for key, value in os.environ.items() if key in {"PATH", "HOME", "SYSTEMROOT", "TMPDIR"}}
        env["COMPOSE_DISABLE_ENV_FILE"] = "1"
        with tempfile.TemporaryDirectory(prefix="alpha-compose-") as temporary:
            mirror = Path(temporary) / "repository"
            for path in sorted(configurations):
                copied = mirror / path.relative_to(root)
                copied.parent.mkdir(parents=True, exist_ok=True)
                copied.write_bytes(path.read_bytes())
                model = yaml.safe_load(path.read_text())
                references = []
                for service in model["services"].values():
                    files = service.get("env_file", [])
                    references.extend(files if isinstance(files, list) else [files])
                for kind in ("secrets", "configs"):
                    references.extend(value["file"] for value in model.get(kind, {}).values() if "file" in value)
                # Compose still stats env files with --no-env-resolution. Empty
                # fixtures preserve the original model and relative paths;
                # neither existing secrets nor application sources are copied.
                for reference in references:
                    name = reference["path"] if isinstance(reference, dict) else reference
                    fixture = (copied.parent / name).resolve()
                    if not fixture.is_relative_to(mirror):
                        raise ValueError("Compose fixture reference escapes its temporary repository")
                    fixture.parent.mkdir(parents=True, exist_ok=True)
                    fixture.touch(exist_ok=True)
                for profiles in ([], ["--profile", "*"]):
                    command = [
                        "docker",
                        "compose",
                        "--env-file",
                        os.devnull,
                        *profiles,
                        "-f",
                        str(copied),
                        "config",
                        "--no-env-resolution",
                        "--format",
                        "json",
                    ]
                    result = subprocess.run(command, cwd=mirror, env=env, capture_output=True, text=True, timeout=30)
                    if result.returncode:
                        raise ValueError(f"Compose rejected {path.relative_to(root)}: {result.stderr}")
                    if "services" not in json.loads(result.stdout):
                        raise ValueError(f"Compose returned no services for {path.relative_to(root)}")
    if args.dev_ui:
        validate_dev_ui(root, args.output.with_name("legacy-compose-failure.json") if args.output else None)
    report = {
        "passed": True,
        "shared_dockerfile_consumers": consumers,
        "local_copy_inputs_resolve": True,
        "compose_default_and_all_profiles_validated": args.docker_compose,
        "operator_secrets_loaded": False,
        "development_ui_modules_loaded": args.dev_ui,
        "research_services_started": False,
    }
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded)


if __name__ == "__main__":
    main()

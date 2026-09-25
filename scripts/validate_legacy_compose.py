#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Validate shared legacy Docker build contexts and optional Compose models."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import urllib.request

import yaml

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def validate_dev_ui(root: Path) -> None:
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
        finally:
            subprocess.run(command + ["down", "--volumes", "--remove-orphans"], env=env, check=True, timeout=60)


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
    if len(consumers) < 7:
        raise ValueError("expected the two core and five demo consumers of the shared Dockerfile")
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
        validate_dev_ui(root)
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

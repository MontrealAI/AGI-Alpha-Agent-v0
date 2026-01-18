# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
"""
This module is part of a conceptual research prototype. References to
'AGI' or 'superintelligence' describe aspirational goals and do not
indicate the presence of real general intelligence. Use at your own risk.

Cross-platform launcher for the AI-GA meta-evolution demo.

This utility mirrors ``run_aiga_demo.sh`` for users without a POSIX shell.
It orchestrates the Docker Compose stack and optionally tails the logs.
Set ``SKIP_DEPS_CHECK=1`` to bypass the environment validation step.
Use ``ALPHA_FACTORY_ENABLE_ADK=1`` to expose the Google ADK gateway and
``ALPHA_FACTORY_FULL=1`` to verify heavy optional packages.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
ROOT_DIR = DEMO_DIR.parent.parent
COMPOSE_YAML = DEMO_DIR / "docker-compose.aiga.yml"
PROJECT = "alpha_aiga"
GHCR_IMAGE = "ghcr.io/montrealai/alpha-aiga:latest"
CONFIG_ENV = DEMO_DIR / "config.env"

# URLs printed after the stack is up -----------------------------------------
DASHBOARD_URL = f"http://localhost:{os.getenv('GRADIO_PORT', '7862')}"
OPENAPI_URL = f"http://localhost:{os.getenv('API_PORT', '8000')}/docs"


def run(cmd: list[str]) -> None:
    """Execute a subprocess command and raise on failure.

    Args:
        cmd: Command and arguments to run.
    """
    subprocess.run(cmd, check=True)


def docker_compose_cmd() -> list[str]:
    """Return the available Docker Compose command."""
    if subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0:
        return ["docker", "compose"]
    if subprocess.run(["docker-compose", "--version"], capture_output=True).returncode == 0:
        return ["docker-compose"]
    sys.exit("docker compose plugin not found")


def ensure_env_file() -> None:
    """Create ``config.env`` if missing."""
    if not CONFIG_ENV.exists():
        print("Creating default config.env (edit to add OPENAI_API_KEY)")
        sample = DEMO_DIR / "config.env.sample"
        CONFIG_ENV.write_bytes(sample.read_bytes())


def ensure_deps() -> None:
    """Run the repo's dependency checker with auto-install enabled."""
    if os.getenv("SKIP_DEPS_CHECK") == "1":
        return
    checker = ROOT_DIR.parent / "check_env.py"
    if checker.exists():
        env = os.environ.copy()
        env["AUTO_INSTALL_MISSING"] = "1"
        result = subprocess.run([sys.executable, str(checker)], env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)
            sys.exit(result.returncode)


def main(argv: list[str] | None = None) -> None:
    """Entry point for launching the demo containers."""
    ap = argparse.ArgumentParser(description="Launch the AI-GA meta-evolution demo")
    ap.add_argument("--pull", action="store_true", help="pull signed image instead of building")
    ap.add_argument("--gpu", action="store_true", help="enable NVIDIA runtime")
    ap.add_argument("--logs", action="store_true", help="tail container logs after start-up")
    ap.add_argument("--reset", action="store_true", help="remove volumes and images")
    ap.add_argument("--stop", action="store_true", help="stop running containers")
    if argv is None and "pytest" in sys.modules:
        if Path(sys.argv[0]).name != Path(__file__).name:
            if not any(flag in {"-h", "--help"} for flag in sys.argv[1:]):
                argv = []
    args = ap.parse_args(argv)

    dc = docker_compose_cmd()
    compose = dc + ["--project-name", PROJECT, "--env-file", str(CONFIG_ENV), "-f", str(COMPOSE_YAML)]

    os.chdir(ROOT_DIR)
    ensure_env_file()
    ensure_deps()

    if args.reset:
        run(compose + ["down", "-v", "--rmi", "all"])
        return
    if args.stop:
        run(compose + ["down"])
        return

    if args.pull:
        run(["docker", "pull", GHCR_IMAGE])

    gpu_args = ["--compatibility", "--profile", "gpu"] if args.gpu else []
    extra = ["--no-build"] if args.pull else []
    run(compose + gpu_args + ["up", "-d", *extra])

    print(f"Dashboard → {DASHBOARD_URL}")
    print(f"OpenAPI  → {OPENAPI_URL}")
    print("Stop     → start_aiga_demo.py --stop")

    if args.logs:
        run(compose + ["logs", "-f"])


if __name__ == "__main__":
    main()

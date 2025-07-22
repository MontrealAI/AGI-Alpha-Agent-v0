#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
"""Interactive environment setup wizard for the Insight demo."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from alpha_factory_v1.utils.disclaimer import print_disclaimer

MIN_PY = (3, 11)
MAX_PY = (3, 13)


def banner(msg: str, color: str = "") -> None:
    """Print *msg* in *color* using ANSI codes."""
    colors = {
        "RED": "\033[91m",
        "GREEN": "\033[92m",
        "YELLOW": "\033[93m",
        "RESET": "\033[0m",
    }
    code = colors.get(color.upper(), "")
    reset = colors["RESET"]
    print(f"{code}{msg}{reset}")


def check_python() -> bool:
    if sys.version_info < MIN_PY or sys.version_info >= MAX_PY:
        banner(
            f"Python {MIN_PY[0]}.{MIN_PY[1]}+ and <{MAX_PY[0]}.{MAX_PY[1]} required",
            "RED",
        )
        return False
    banner(f"Python {sys.version.split()[0]} detected", "GREEN")
    return True


def check_cmd(cmd: str) -> bool:
    if shutil.which(cmd):
        banner(f"{cmd} found", "GREEN")
        return True
    banner(f"{cmd} missing", "RED")
    return False


def check_node() -> bool:
    if not shutil.which("node"):
        banner("node missing", "RED")
        return False
    try:
        out = subprocess.check_output(["node", "--version"], text=True).strip()
    except Exception:
        banner("failed to run node --version", "RED")
        return False
    banner(f"Node {out} detected", "GREEN")
    if not out.lstrip("v").startswith("22"):
        banner("Node 22 recommended", "YELLOW")
    return True


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=False)


def main() -> None:
    print_disclaimer()
    banner("Alpha-Factory Setup Wizard", "YELLOW")
    ok = True
    ok &= check_python()
    ok &= check_cmd("git")
    ok &= check_cmd("docker")
    ok &= check_node()

    if not ok:
        banner("Some dependencies are missing", "RED")
    else:
        banner("Environment looks good", "GREEN")

    repo_root = Path(__file__).resolve().parents[1]
    while True:
        print()
        print("Select an option:")
        print("1) Run check_env.py --auto-install")
        print("2) Run ./codex/setup.sh")
        print("3) Start Insight demo with ./quickstart.sh")
        print("4) Start Insight demo in Docker (docker compose up)")
        print("5) Exit")
        choice = input("Enter choice: ").strip()
        if choice == "1":
            run([sys.executable, str(repo_root / "check_env.py"), "--auto-install"])
        elif choice == "2":
            run([str(repo_root / "codex" / "setup.sh")])
        elif choice == "3":
            run([str(repo_root / "quickstart.sh")])
        elif choice == "4":
            run(["docker", "compose", "up"])
        elif choice == "5":
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()

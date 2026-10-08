#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# See docs/DISCLAIMER_SNIPPET.md
"""Interactive environment setup wizard for the Insight demo."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# A setup helper must work before the checkout is installed, including direct
# invocation by absolute path from another directory.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_factory_v1.utils.disclaimer import print_disclaimer  # noqa: E402

MIN_PY = (3, 11)
MAX_PY = (3, 14)


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


def run(cmd: list[str]) -> bool:
    """Run one selected action from the checkout and leave errors visible for recovery."""
    try:
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        banner(f"Command failed with exit status {exc.returncode}. Review the error above before retrying.", "RED")
        return False
    except OSError as exc:
        banner(f"Could not start the command: {exc}. Check the required tool and try again.", "RED")
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    """Offer explicit source-checkout setup actions without installing on startup."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Requires Python 3.11–3.13. Actions run from this checkout's root. Installation options may download "
            "dependencies; launch options may start services. Choose an action explicitly, or 5 to exit. "
            "For the minimal native agent, use the release's install_agent.py instead."
        ),
    )
    parser.parse_args(argv)
    print_disclaimer()
    banner("Alpha-Factory Setup Wizard", "YELLOW")
    if not check_python():
        banner("Restart with a supported Python interpreter before installing or launching services.", "RED")
        return 1
    ok = True
    ok &= check_cmd("git")
    ok &= check_cmd("docker")
    ok &= check_node()

    if not ok:
        banner("Some dependencies are missing", "RED")
    else:
        banner("Environment looks good", "GREEN")

    print(f"Working checkout: {REPO_ROOT}")
    while True:
        print()
        print("Select an option:")
        print("1) Run check_env.py --auto-install")
        print("2) Run ./codex/setup.sh")
        print("3) Start Insight demo with ./quickstart.sh")
        print("4) Start Insight demo in Docker (docker compose up)")
        print("5) Exit")
        try:
            choice = input("Enter choice: ").strip()
            if choice == "1":
                run([sys.executable, str(REPO_ROOT / "check_env.py"), "--auto-install"])
            elif choice == "2":
                run([str(REPO_ROOT / "codex" / "setup.sh")])
            elif choice == "3":
                run([str(REPO_ROOT / "quickstart.sh")])
            elif choice == "4":
                run(["docker", "compose", "up"])
            elif choice == "5":
                return 0
            else:
                print("Invalid choice; enter a number from 1 to 5.")
        except EOFError:
            print("\nSetup wizard closed; no further action was started.")
            return 0
        except KeyboardInterrupt:
            print("\nSetup wizard interrupted. Check any running services before retrying.")
            return 130


if __name__ == "__main__":
    raise SystemExit(main())

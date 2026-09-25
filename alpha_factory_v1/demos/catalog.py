# SPDX-License-Identifier: Apache-2.0
"""One catalog for demo launch instructions, gallery descriptions and validation."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any

from alpha_factory_v1.utils.disclaimer import print_disclaimer

CATALOG = Path(__file__).with_name("catalog.json")
REPO_ROOT = Path(__file__).resolve().parents[2]
GALLERY = "https://montrealai.github.io/AGI-Alpha-Agent-v0/"


def entries() -> list[dict[str, Any]]:
    """Load the reviewed demo inventory without importing optional backends."""
    return json.loads(CATALOG.read_text(encoding="utf-8"))["entries"]  # type: ignore[no-any-return]


def command_for(entry: dict[str, Any], output: Path) -> list[str]:
    """Resolve a fixed argument vector; no shell or user-supplied code is used."""
    return [
        sys.executable if arg == "python" and i == 0 else arg.replace("{output}", str(output.resolve()))
        for i, arg in enumerate(entry["command"])
    ]


def environment_for(entry: dict[str, Any], output: Path) -> dict[str, str]:
    """Resolve explicitly declared demo settings and keep output outside the source."""
    env = os.environ.copy()
    env.update({key: value.replace("{output}", str(output.resolve())) for key, value in entry["environment"].items()})
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("AF_MEMORY_DIR", str(output.resolve() / "memory"))
    env.setdefault("AF_TRACING", "false")
    return env


def main(argv: list[str] | None = None) -> int:
    """List, inspect or launch a documented demo with explicit expectations."""
    parser = argparse.ArgumentParser(description="Explore the AGIALPHA demo catalog")
    sub = parser.add_subparsers(dest="action")
    listing = sub.add_parser("list", help="List every demo and its execution mode")
    listing.add_argument("--json", action="store_true")
    for name in ("show", "run"):
        child = sub.add_parser(name, help="Show a guide" if name == "show" else "Run the documented local command")
        child.add_argument("demo", choices=[entry["id"] for entry in entries()])
        child.add_argument("--output-dir", type=Path, help="Directory for this demo's local state")
    args = parser.parse_args(argv)
    if args.action is None:
        parser.print_help()
        return 0
    if args.action == "list":
        if args.json:
            print(json.dumps(entries(), indent=2, ensure_ascii=False))
        else:
            for entry in entries():
                print(f"{entry['id']:<38} {entry['mode']}")
            print("\nStart: python -m alpha_factory_v1.demos show DEMO_NAME")
        return 0
    entry = next(item for item in entries() if item["id"] == args.demo)
    output = args.output_dir or Path.cwd() / "demo-runs" / entry["id"]
    print(f"\n{entry['title']} — {entry['mode']}\n{entry['summary']}")
    print(f"\nPrerequisites: {entry['prerequisites']}\nExpected: {entry['expected']}")
    print(f"Scope: {entry['limitations']}\nBrowser/guide: {GALLERY}demos/{entry['id']}/")
    command = command_for(entry, output)
    if not command:
        print("This entry has no supported standalone CLI. Use its browser illustration and guide.")
        return 0 if args.action == "show" else 2
    print(f"\nCommand: {shlex.join(command)}\nOutput directory: {output.resolve()}", flush=True)
    if entry["environment"]:
        print("Demo settings: " + ", ".join(entry["environment"]), flush=True)
    if args.action == "show":
        return 0
    print_disclaimer()
    output.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.run(command, cwd=output, env=environment_for(entry, output), check=False).returncode
    except KeyboardInterrupt:
        print("\nStopped. Local output is retained.", file=sys.stderr)
        return 130
    except OSError as exc:
        print(f"Could not launch: {exc}. Check the prerequisites above.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
